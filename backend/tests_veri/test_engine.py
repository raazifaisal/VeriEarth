"""Engine tests. They run offline against the cached hazard snapshot for 2026-09-22."""
import copy
from datetime import date

import pytest

from veri import engine, planner
from veri.model import load_network

AS_OF = date(2026, 9, 22)


@pytest.fixture(scope="module")
def a():
    return engine.assess(AS_OF, n=1500, seed=3)


def test_network_loads_and_validates():
    net = load_network()
    assert net.suppliers()
    assert all(p.bom for p in net.products.values())


def test_simulation_is_deterministic():
    a1 = engine.assess(AS_OF, n=500, seed=11)
    engine.assess.cache_clear()
    a2 = engine.assess(AS_OF, n=500, seed=11)
    assert a1.sim.revenue_at_risk.sum() == pytest.approx(a2.sim.revenue_at_risk.sum())


def test_low_lying_suppliers_riskier_than_high_ground(a):
    p = a.sim.site_p_down
    assert p["S-RESIN"] > p["S-STAMP"]  # ~6 m Amata City Chonburi vs ~70 m Pinthong


def test_criticality_ranks_single_source_resin_first(a):
    rows = a.criticality()
    assert rows[0]["supplier"] == "S-RESIN"
    assert {r["quadrant"] for r in rows} <= {"act_now", "build_buffers", "monitor", "low"}


def test_all_presets_pass_verifier(a):
    plans = a.plans
    assert plans
    for p in plans:
        v = engine.verify_plan(a, p.to_dict())
        assert v["ok"], (p.name, v["issues"])


def test_verifier_catches_tampered_co2(a):
    plan = copy.deepcopy(a.plans[0].to_dict())
    line = next(l for l in plan["lines"].values() if any(x["kind"] != "unmet" for x in l))
    alloc = next(x for x in line if x["kind"] != "unmet")
    alloc["co2_kg"] = alloc["co2_kg"] * 0.2 + 0.0  # an LLM "rounding down" emissions
    v = engine.verify_plan(a, plan)
    assert not v["ok"]
    assert any("CO2" in i for i in v["issues"])


def test_verifier_catches_uncovered_shortage(a):
    plan = copy.deepcopy(a.plans[0].to_dict())
    key = next(iter(plan["lines"]))
    plan["lines"][key] = plan["lines"][key][:-1] if len(plan["lines"][key]) > 1 else []
    assert not engine.verify_plan(a, plan)["ok"]


def test_deciding_early_beats_deciding_after_event():
    t = engine.compare_timing(AS_OF)
    assert t["decide_now"]["total_cost_thb"] < t["decide_after_event"]["total_cost_thb"]
    assert t["decide_now"]["co2_kg"] < t["decide_after_event"]["co2_kg"]


def test_carbon_preset_never_emits_more_than_cheapest(a):
    plans = {p.name: p for p in a.plans}
    assert plans["Lowest carbon, same protection"].co2_kg <= plans["Lowest total cost"].co2_kg + 1e-6


def test_pareto_is_monotone(a):
    pts = planner.pareto(a.net, a.sim, steps=5)
    costs = [p["total_cost_thb"] for p in sorted(pts, key=lambda p: p["co2_cap_kg"])]
    assert all(c1 >= c2 - 1 for c1, c2 in zip(costs, costs[1:]))
