"""Mitigation planner: choose how to cover each forecast part shortage, trading
cost, lost revenue and CO2. Solved as a small LP with OR-Tools (GLOP).

Options per (part, plant) shortage:
- prebuild:  pull deliveries forward from the at-risk supplier before the event
             (only possible when the forecast gives warning time)
- alternate: qualified alternate suppliers, by their contracted mode and lead time
- unmet:     accept the shortage and lose the revenue

The LLM never writes this model. It can only pick an objective preset and
explain the result; the verifier re-checks every number independently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from ortools.linear_solver import pywraplp

from . import emissions as em
from .model import Network
from .simulate import SimResult

SHORTAGE_QUANTILE = 80      # plan for the P80 shortage (risk-averse)
PREBUILD_SURGE = 0.6        # supplier can ship +60% of normal volume before the event
PREBUILD_PREMIUM = 0.03     # overtime / expedite premium on pulled-forward volume
ALT_UNAVAILABLE_ABOVE = 0.5  # skip alternates likely to be down themselves


@dataclass
class Option:
    key: str
    kind: str                 # prebuild | alternate | unmet
    part: str
    plant: str
    supplier: str
    mode: str
    lead_days: float
    capacity_units: float
    unit_cost_thb: float      # purchase + freight per part unit (penalty for unmet)
    unit_co2_kg: float
    legs: list[dict] = field(default_factory=list)
    note: str = ""


@dataclass
class Need:
    part: str
    plant: str
    supplier: str
    demand_per_day: float
    shortage_days: float
    units: float
    starts_in_days: float
    options: list[Option]


@dataclass
class Allocation:
    option: str
    kind: str
    supplier: str
    mode: str
    units: float
    cost_thb: float
    co2_kg: float


@dataclass
class Plan:
    name: str
    objective: str
    decided_days_before_event: float
    total_cost_thb: float
    purchase_and_freight_thb: float
    lost_revenue_thb: float
    co2_kg: float
    coverage: float
    lines: dict[str, list[Allocation]]
    needs: dict[str, dict]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["lines"] = {k: [asdict(a) for a in v] for k, v in self.lines.items()}
        return d


def _lost_revenue_per_part_unit(net: Network, part: str, plant: str) -> float:
    rev = sum(p.daily_rate * p.unit_price_thb for p in net.products.values() if p.plant == plant and part in p.bom)
    use = net.part_demand_per_day(plant, part)
    return rev / use if use else 0.0


def build_needs(net: Network, sim: SimResult, delay_days: float = 0.0) -> list[Need]:
    """Shortages worth planning for. `delay_days` simulates deciding later (e.g. after the event)."""
    needs = []
    for sp in net.supplies:
        days = np.percentile(sim.part_shortage_days[(sp.part, sp.plant)], SHORTAGE_QUANTILE)
        if days <= 0:
            continue
        part = net.parts[sp.part]
        demand = net.part_demand_per_day(sp.plant, sp.part)
        units = demand * float(days)
        event_in = sim.site_event_day.get(sp.supplier, 0) + 1 - delay_days    # days until supplier stops
        starts_in = event_in + sp.inventory_days                               # days until line runs short
        ends_in = starts_in + float(days)
        opts: list[Option] = []

        if event_in >= 1:
            cap = PREBUILD_SURGE * demand * event_in
            legs = em.route(net, sp.supplier, sp.plant, "road_truck", None)
            t = part.unit_weight_kg / 1000.0
            opts.append(Option(
                key=f"{sp.part}@{sp.plant}:prebuild", kind="prebuild", part=sp.part, plant=sp.plant,
                supplier=sp.supplier, mode="road_truck", lead_days=1, capacity_units=cap,
                unit_cost_thb=part.unit_cost_thb * (1 + PREBUILD_PREMIUM) + em.freight_cost_thb(legs, t),
                unit_co2_kg=em.co2_kg(legs, t), legs=[asdict(l) for l in legs],
                note=f"Pull forward {PREBUILD_SURGE:.0%} extra volume for {event_in:.0f} days before the forecast peak",
            ))

        for term in net.alternate_terms:
            if term.part != sp.part or term.supplier not in sp.alternates:
                continue
            p_alt = sim.site_p_down.get(term.supplier, 0.0)
            if p_alt > ALT_UNAVAILABLE_ABOVE:
                continue
            useful_from = max(term.lead_days, starts_in)
            useful_days = max(0.0, ends_in - useful_from)
            cap = term.max_share_of_demand * demand * useful_days * (1 - p_alt)
            if cap <= 0:
                continue
            legs = em.route(net, term.supplier, sp.plant, term.mode, term.via)
            t = part.unit_weight_kg / 1000.0
            opts.append(Option(
                key=f"{sp.part}@{sp.plant}:{term.supplier}:{term.mode}", kind="alternate", part=sp.part,
                plant=sp.plant, supplier=term.supplier, mode=term.mode, lead_days=term.lead_days,
                capacity_units=cap,
                unit_cost_thb=part.unit_cost_thb * (1 + term.price_premium) + em.freight_cost_thb(legs, t),
                unit_co2_kg=em.co2_kg(legs, t), legs=[asdict(l) for l in legs],
                note=f"{net.sites[term.supplier].name}, {term.mode}, lead {term.lead_days:g} d, P(down)={p_alt:.2f}",
            ))

        opts.append(Option(
            key=f"{sp.part}@{sp.plant}:unmet", kind="unmet", part=sp.part, plant=sp.plant, supplier="-",
            mode="-", lead_days=0, capacity_units=units,
            unit_cost_thb=_lost_revenue_per_part_unit(net, sp.part, sp.plant), unit_co2_kg=0.0,
            note="Accept the shortage: lost production and late customer orders",
        ))
        needs.append(Need(sp.part, sp.plant, sp.supplier, demand, float(days), units, starts_in, opts))
    return needs


def solve(needs: list[Need], co2_cap_kg: float | None = None, lost_revenue_cap_thb: float | None = None,
          minimise: str = "cost") -> dict[str, float] | None:
    """Return units per option key, or None if infeasible.

    minimise: "cost" (spend + lost revenue) or "co2". Caps are optional constraints.
    """
    s = pywraplp.Solver.CreateSolver("GLOP")
    x = {}
    for nd in needs:
        row = []
        for o in nd.options:
            v = s.NumVar(0, o.capacity_units, o.key)
            x[o.key] = (v, o)
            row.append(v)
        s.Add(sum(row) == nd.units)
    co2 = sum(v * o.unit_co2_kg for v, o in x.values())
    cost = sum(v * o.unit_cost_thb for v, o in x.values())
    lost = sum(v * o.unit_cost_thb for v, o in x.values() if o.kind == "unmet")
    if co2_cap_kg is not None:
        s.Add(co2 <= co2_cap_kg)
    if lost_revenue_cap_thb is not None:
        s.Add(lost <= lost_revenue_cap_thb)
    s.Minimize(cost if minimise == "cost" else co2)
    if s.Solve() != pywraplp.Solver.OPTIMAL:
        return None
    return {k: v.solution_value() for k, (v, _) in x.items()}


def to_plan(name: str, objective: str, needs: list[Need], sol: dict[str, float], decided_before: float) -> Plan:
    lines: dict[str, list[Allocation]] = {}
    total = purchase = lost = co2 = covered = need_units = 0.0
    for nd in needs:
        key = f"{nd.part}@{nd.plant}"
        lines[key] = []
        need_units += nd.units
        for o in nd.options:
            u = sol.get(o.key, 0.0)
            if u <= 1e-6:
                continue
            c, e = u * o.unit_cost_thb, u * o.unit_co2_kg
            lines[key].append(Allocation(o.key, o.kind, o.supplier, o.mode, round(u, 1), round(c), round(e, 1)))
            total += c
            co2 += e
            if o.kind == "unmet":
                lost += c
            else:
                purchase += c
                covered += u
    return Plan(
        name=name, objective=objective, decided_days_before_event=decided_before,
        total_cost_thb=round(total), purchase_and_freight_thb=round(purchase), lost_revenue_thb=round(lost),
        co2_kg=round(co2, 1), coverage=round(covered / need_units, 3) if need_units else 1.0, lines=lines,
        needs={f"{n.part}@{n.plant}": {"supplier": n.supplier, "units": round(n.units), "shortage_days_p80": n.shortage_days,
                                       "starts_in_days": n.starts_in_days, "demand_per_day": n.demand_per_day,
                                       "options": [asdict(o) for o in n.options]} for n in needs},
    )


def plan_options(net: Network, sim: SimResult, decide_delay_days: float = 0.0) -> list[Plan]:
    """Three named plans plus the cost-CO2 Pareto front, at the given decision time."""
    needs = build_needs(net, sim, decide_delay_days)
    if not needs:
        return []
    lead = sim_lead(sim) - decide_delay_days
    cheapest = to_plan("Lowest total cost", "min spend + lost revenue", needs, solve(needs), lead)
    plans = [cheapest]
    # Same protection (lost revenue no worse than +2%), minimum carbon.
    green = solve(needs, lost_revenue_cap_thb=cheapest.lost_revenue_thb * 1.02 + 1, minimise="co2")
    if green:
        plans.append(to_plan("Lowest carbon, same protection", "min CO2 with lost revenue within 2% of the cheapest plan",
                             needs, green, lead))
    # Cheapest plan that halves the carbon of the lowest-cost plan.
    half = solve(needs, co2_cap_kg=0.5 * cheapest.co2_kg)
    if half and cheapest.co2_kg > 0:
        plans.append(to_plan("Half the carbon", f"min cost with CO2 <= {0.5 * cheapest.co2_kg:,.0f} kg", needs, half, lead))
    return plans


def pareto(net: Network, sim: SimResult, steps: int = 8, decide_delay_days: float = 0.0) -> list[dict]:
    needs = build_needs(net, sim, decide_delay_days)
    if not needs:
        return []
    hi = to_plan("", "", needs, solve(needs), 0).co2_kg
    pts = []
    for i in range(steps + 1):
        cap = hi * i / steps
        sol = solve(needs, co2_cap_kg=cap)
        if sol:
            p = to_plan("", "", needs, sol, 0)
            pts.append({"co2_cap_kg": round(cap, 1), "co2_kg": p.co2_kg, "total_cost_thb": p.total_cost_thb,
                        "lost_revenue_thb": p.lost_revenue_thb, "coverage": p.coverage})
    return pts


def sim_lead(sim: SimResult) -> float:
    """Typical warning time: median days from decision to the first supplier event."""
    days = [d + 1 for s, d in sim.site_event_day.items() if sim.site_p_down.get(s, 0) > 0.1]
    return float(np.median(days)) if days else 0.0
