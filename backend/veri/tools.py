"""Engine functions exposed to the Gemini agents as tools.

Every number an agent reports must come from one of these functions. Plans are
kept in a per-process store so agents refer to them by id instead of retyping
numbers.
"""
from __future__ import annotations

import copy
import itertools
from datetime import date

from . import engine, planner

_PLANS: dict[str, dict] = {}
_ids = itertools.count(1)
_AS_OF = {"value": engine.DEFAULT_AS_OF}


def set_decision_date(as_of: str) -> dict:
    """Set the decision date (YYYY-MM-DD) that all other tools use. The demo hindcast uses 2026-09-22."""
    _AS_OF["value"] = date.fromisoformat(as_of)
    return {"as_of": as_of}


def _a():
    return engine.assess(_AS_OF["value"])


def _m(x: float) -> float:
    return round(x / 1e6, 2)


def get_risk_overview() -> dict:
    """Revenue at risk over the planning horizon, late-order probabilities and joint failures
    of primary and alternate suppliers, for the current decision date."""
    ov = engine.overview(_a())
    rr = ov["revenue_at_risk"]
    return {
        "as_of": ov["as_of"], "company": ov["company"], "illustrative_network": ov["illustrative_network"],
        "horizon_days": ov["horizon_days"], "warning_days": ov["warning_days"],
        "revenue_at_risk_million_thb": {"expected": _m(rr["expected_revenue_at_risk_thb"]), "p50": _m(rr["p50_thb"]),
                                        "p90": _m(rr["p90_thb"])},
        "p_any_loss": round(rr["p_any_loss"], 3),
        "orders": ov["orders"],
        "joint_failure": ov["joint_failure"],
    }


def rank_supplier_criticality() -> dict:
    """Suppliers ranked by live criticality (expected revenue at risk), with structural criticality
    (14-day stress test), exposure (probability the site goes down), time-to-survive and quadrant
    (act_now, build_buffers, monitor, low)."""
    rows = _a().criticality()
    for r in rows:
        for k in ("structural_rar_thb", "live_expected_rar_thb", "live_p90_rar_thb"):
            r[k.replace("_thb", "_million_thb")] = _m(r.pop(k))
    return {"as_of": _a().as_of, "suppliers": rows}


def explain_site_risk(site_id: str) -> dict:
    """Hazard inputs and model terms behind one site's disruption probability: forecast rain by
    ensemble member, antecedent rain, elevation and each term's contribution to the log-odds."""
    a = _a()
    if site_id not in a.snap.sites:
        return {"error": f"unknown or unmonitored site {site_id}", "known": sorted(a.snap.sites)}
    return a.site_detail(site_id)


def _summarise(plan_id: str, p: dict) -> dict:
    return {
        "plan_id": plan_id, "name": p["name"], "objective": p["objective"],
        "total_cost_million_thb": _m(p["total_cost_thb"]),
        "spend_million_thb": _m(p["purchase_and_freight_thb"]),
        "lost_revenue_million_thb": _m(p["lost_revenue_thb"]),
        "co2_tonnes": round(p["co2_kg"] / 1000, 2), "coverage": p["coverage"],
        "actions": {k: [{"option": x["option"], "kind": x["kind"], "supplier": x["supplier"], "mode": x["mode"],
                         "units": x["units"]} for x in v] for k, v in p["lines"].items()},
    }


def propose_mitigation_plans() -> dict:
    """Solve the mitigation LP (OR-Tools) and return the preset plans: lowest total cost, lowest
    carbon with the same protection, and half the carbon. Each plan gets a plan_id."""
    out = []
    for p in _a().plans:
        pid = f"P{next(_ids)}"
        _PLANS[pid] = p.to_dict()
        out.append(_summarise(pid, _PLANS[pid]))
    return {"as_of": _a().as_of, "plans": out}


def list_options(part_at_plant: str, plan_id: str) -> dict:
    """The available options for one shortage (key like 'PP-COMP@SIC-P1') in a plan, with capacity,
    lead time, unit cost and unit CO2 for each."""
    p = _PLANS.get(plan_id)
    if not p or part_at_plant not in p["needs"]:
        return {"error": "unknown plan or shortage", "plans": list(_PLANS), "shortages": list(p["needs"]) if p else []}
    need = p["needs"][part_at_plant]
    return {"need_units": need["units"], "shortage_days_p80": need["shortage_days_p80"],
            "starts_in_days": need["starts_in_days"],
            "options": [{k: o[k] for k in ("key", "kind", "supplier", "mode", "lead_days", "capacity_units",
                                           "unit_cost_thb", "unit_co2_kg", "note")} for o in need["options"]]}


def adjust_plan(plan_id: str, part_at_plant: str, option_key: str, units: float) -> dict:
    """Create a new plan from `plan_id` that moves `units` of one shortage onto `option_key`, taking
    them from the shortage's other allocations (unmet first). Costs and CO2 are recomputed from the
    option's unit rates. The result must still pass verify_plan before it can be recommended."""
    base = _PLANS.get(plan_id)
    if not base or part_at_plant not in base["needs"]:
        return {"error": "unknown plan or shortage"}
    p = copy.deepcopy(base)
    opts = {o["key"]: o for o in p["needs"][part_at_plant]["options"]}
    if option_key not in opts:
        return {"error": f"unknown option {option_key}", "options": list(opts)}
    line = p["lines"][part_at_plant]
    by_key = {x["option"]: x for x in line}
    remaining = float(units)
    order = sorted(line, key=lambda x: (x["kind"] != "unmet", -x["units"]))
    for x in order:
        if x["option"] == option_key or remaining <= 0:
            continue
        take = min(x["units"], remaining)
        x["units"] -= take
        remaining -= take
    moved = float(units) - remaining
    tgt = by_key.get(option_key) or {"option": option_key, "kind": opts[option_key]["kind"],
                                     "supplier": opts[option_key]["supplier"], "mode": opts[option_key]["mode"],
                                     "units": 0.0, "cost_thb": 0.0, "co2_kg": 0.0}
    if option_key not in by_key:
        line.append(tgt)
    tgt["units"] += moved
    for x in line:
        o = opts[x["option"]]
        x["units"] = round(x["units"], 1)
        x["cost_thb"] = round(x["units"] * o["unit_cost_thb"])
        x["co2_kg"] = round(x["units"] * o["unit_co2_kg"], 1)
    p["lines"][part_at_plant] = [x for x in line if x["units"] > 0]
    allocs = [x for v in p["lines"].values() for x in v]
    p["total_cost_thb"] = round(sum(x["cost_thb"] for x in allocs))
    p["co2_kg"] = round(sum(x["co2_kg"] for x in allocs), 1)
    p["lost_revenue_thb"] = round(sum(x["cost_thb"] for x in allocs if x["kind"] == "unmet"))
    p["purchase_and_freight_thb"] = p["total_cost_thb"] - p["lost_revenue_thb"]
    need_total = sum(n["units"] for n in p["needs"].values())
    p["coverage"] = round(sum(x["units"] for x in allocs if x["kind"] != "unmet") / need_total, 3)
    p["name"] = f"{base['name']} (edited)"
    pid = f"P{next(_ids)}"
    _PLANS[pid] = p
    return _summarise(pid, p)


def verify_plan(plan_id: str) -> dict:
    """Independently recompute a plan's cost and CO2 from the network and emission factors, and check
    coverage, capacity, lead times and alternate availability. Returns ok and a list of issues."""
    p = _PLANS.get(plan_id)
    if not p:
        return {"error": f"unknown plan {plan_id}", "plans": list(_PLANS)}
    v = engine.verify_plan(_a(), p)
    v["plan_id"] = plan_id
    return v


def compare_decision_timing() -> dict:
    """Cost and CO2 of the lowest-cost plan if decided now (with forecast warning) versus after the
    event hits, when pre-building is impossible and slow low-carbon options arrive too late."""
    t = engine.compare_timing(_AS_OF["value"])
    s = lambda p: None if p is None else {"total_cost_million_thb": _m(p["total_cost_thb"]),
                                          "co2_tonnes": round(p["co2_kg"] / 1000, 2), "coverage": p["coverage"]}
    return {"warning_days": t["warning_days"], "decide_now": s(t["decide_now"]),
            "decide_after_event": s(t["decide_after_event"])}


def get_plan(plan_id: str) -> dict:
    """Full detail of a stored plan, including every allocation's cost and CO2."""
    p = _PLANS.get(plan_id)
    return p if p else {"error": f"unknown plan {plan_id}", "plans": list(_PLANS)}


def pareto_front() -> dict:
    """Total cost (spend + lost revenue) versus CO2 cap: the trade-off curve for the current decision."""
    a = _a()
    return {"points": planner.pareto(a.net, a.sim)}


HAZARD_TOOLS = [get_risk_overview, explain_site_risk]
CRITICALITY_TOOLS = [rank_supplier_criticality, get_risk_overview]
PLANNER_TOOLS = [propose_mitigation_plans, list_options, adjust_plan, compare_decision_timing, pareto_front, get_plan]
VERIFIER_TOOLS = [verify_plan, get_plan]
