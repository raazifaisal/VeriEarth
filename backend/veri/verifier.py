"""Independent plan verifier.

Recomputes every allocation's cost and CO2 from the network and emission
factors (not from the planner's cached option values), and checks coverage,
capacities, lead-time feasibility and alternate availability. Any plan,
including one proposed or edited by an LLM, must pass before it is shown as
a recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import emissions as em
from .model import Network
from .simulate import SimResult

REL_TOL = 0.01


@dataclass
class Verdict:
    ok: bool
    issues: list[str] = field(default_factory=list)
    recomputed_cost_thb: float = 0.0
    recomputed_co2_kg: float = 0.0

    def to_dict(self) -> dict:
        return {"ok": self.ok, "issues": self.issues,
                "recomputed_cost_thb": round(self.recomputed_cost_thb),
                "recomputed_co2_kg": round(self.recomputed_co2_kg, 1)}


ABS_TOL = 1.0  # plans report CO2 to 0.1 kg and cost to 1 THB


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def verify(net: Network, sim: SimResult, plan: dict) -> Verdict:
    """`plan` is Plan.to_dict(), or an edited copy of it."""
    issues: list[str] = []
    total_cost = total_co2 = 0.0
    terms = {(t.supplier, t.part, t.mode): t for t in net.alternate_terms}

    for key, allocs in plan["lines"].items():
        need = plan["needs"].get(key)
        if need is None:
            issues.append(f"{key}: allocation for a shortage that is not in the forecast")
            continue
        part_id, plant = key.split("@")
        part = net.parts[part_id]
        t = part.unit_weight_kg / 1000.0
        options = {o["key"]: o for o in need["options"]}
        units_sum = 0.0
        for a in allocs:
            u = a["units"]
            units_sum += u
            if u < 0:
                issues.append(f"{a['option']}: negative quantity")
            opt = options.get(a["option"])
            if opt is None:
                issues.append(f"{a['option']}: not an available option for {key}")
                continue
            if u > opt["capacity_units"] * (1 + REL_TOL):
                issues.append(f"{a['option']}: {u:,.0f} units exceeds capacity {opt['capacity_units']:,.0f}")

            if a["kind"] == "unmet":
                cost = u * opt["unit_cost_thb"]
                co2 = 0.0
            else:
                if a["kind"] == "alternate":
                    term = terms.get((a["supplier"], part_id, a["mode"]))
                    if term is None:
                        issues.append(f"{a['option']}: no contract terms for {a['supplier']} by {a['mode']}")
                        continue
                    if sim.site_p_down.get(a["supplier"], 0.0) > 0.5:
                        issues.append(f"{a['option']}: alternate is itself likely to be down")
                    if term.lead_days > need["starts_in_days"] + need["shortage_days_p80"]:
                        issues.append(f"{a['option']}: arrives after the shortage is over")
                    legs = em.route(net, a["supplier"], plant, term.mode, term.via)
                    unit_price = part.unit_cost_thb * (1 + term.price_premium)
                else:  # prebuild
                    legs = em.route(net, a["supplier"], plant, "road_truck", None)
                    unit_price = part.unit_cost_thb * 1.03
                cost = u * (unit_price + em.freight_cost_thb(legs, t))
                co2 = u * em.co2_kg(legs, t)

            if not _close(cost, a["cost_thb"]):
                issues.append(f"{a['option']}: cost {a['cost_thb']:,.0f} does not match recomputed {cost:,.0f}")
            if not _close(co2, a["co2_kg"]):
                issues.append(f"{a['option']}: CO2 {a['co2_kg']:,.1f} kg does not match recomputed {co2:,.1f}")
            total_cost += cost
            total_co2 += co2

        if not _close(units_sum, need["units"]):
            issues.append(f"{key}: allocations sum to {units_sum:,.0f}, need is {need['units']:,.0f}")

    if not _close(total_cost, plan["total_cost_thb"]):
        issues.append(f"plan total cost {plan['total_cost_thb']:,.0f} vs recomputed {total_cost:,.0f}")
    if not _close(total_co2, plan["co2_kg"]):
        issues.append(f"plan CO2 {plan['co2_kg']:,.1f} kg vs recomputed {total_co2:,.1f}")
    return Verdict(not issues, issues, total_cost, total_co2)
