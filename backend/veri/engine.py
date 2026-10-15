"""One call that runs the whole loop for a decision date: hazard -> simulation ->
criticality -> plans -> verification. Results are plain dicts for the API and agents.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

from . import criticality, planner, verifier
from .hazard import HazardSnapshot, load_or_fetch
from .model import Network, load_network
from .simulate import SimResult, run
from .vulnerability import SiteFactors, explain

DEFAULT_AS_OF = date(2026, 9, 22)   # 3 days before the 25-27 Sep 2026 rain peak


@dataclass
class Assessment:
    as_of: str
    net: Network
    snap: HazardSnapshot
    sim: SimResult

    @property
    def plans(self) -> list[planner.Plan]:
        return planner.plan_options(self.net, self.sim)

    def criticality(self) -> list[dict]:
        return [r.to_dict() for r in criticality.assess(self.net, self.sim)]

    def site_detail(self, site_id: str) -> dict:
        h = self.snap.sites[site_id]
        members = h.forecast_max3_by_member
        f = SiteFactors(sorted(members)[len(members) // 2], h.antecedent_mm, h.elevation_m)
        s = self.net.sites[site_id]
        return {
            "site": site_id, "name": s.name, "estate": s.estate, "lat": s.lat, "lon": s.lon,
            "elevation_m": h.elevation_m, "antecedent_14d_mm": h.antecedent_mm,
            "forecast_max_3day_mm_by_member": [round(m) for m in members],
            "observed_max_3day_mm": round(h.observed_max3),
            "forecast_daily_mm": h.forecast_daily_mm,
            "model_terms_at_median_forecast": explain(f),
            "simulated_p_down": round(self.sim.site_p_down.get(site_id, 0.0), 3),
            "simulated_median_downtime_days": round(self.sim.site_downtime_p50.get(site_id, 0.0), 1),
            "hazard_source": self.snap.source,
        }


@lru_cache(maxsize=16)
def assess(as_of: date = DEFAULT_AS_OF, n: int = 4000, seed: int = 7) -> Assessment:
    net = load_network()
    snap = load_or_fetch(net, as_of)
    sim = run(net, snap, n=n, seed=seed)
    return Assessment(as_of.isoformat(), net, snap, sim)


def overview(a: Assessment) -> dict:
    s = a.sim.summary()
    return {
        "as_of": a.as_of,
        "company": a.net.company["name"],
        "illustrative_network": a.net.meta.get("illustrative", True),
        "horizon_days": a.net.horizon_days,
        "revenue_at_risk": s,
        "orders": [{"id": o.id, "customer": a.net.sites[o.customer].name, "product": o.product,
                    "qty": o.qty, "due": (date.fromisoformat(a.as_of) + timedelta(days=o.due_offset_days)).isoformat(),
                    "p_late": round(a.sim.order_p_late[o.id], 3)} for o in a.net.orders],
        "joint_failure": [{"primary": k[0], "alternate": k[1], "p_both_down": round(v, 3)} for k, v in a.sim.joint_down.items()],
        "warning_days": planner.sim_lead(a.sim),
    }


def compare_timing(as_of: date = DEFAULT_AS_OF) -> dict:
    """Decide now (with forecast warning) vs decide after the event hits (reactive)."""
    a = assess(as_of)
    lead = planner.sim_lead(a.sim)
    early = planner.plan_options(a.net, a.sim, 0.0)
    late = planner.plan_options(a.net, a.sim, lead)
    pick = lambda plans: plans[0].to_dict() if plans else None
    return {"warning_days": lead, "decide_now": pick(early), "decide_after_event": pick(late)}


def verify_plan(a: Assessment, plan: dict) -> dict:
    return verifier.verify(a.net, a.sim, plan).to_dict()
