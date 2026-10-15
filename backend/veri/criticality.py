"""Supplier criticality = structural criticality (slow) x current exposure (fast).

- Structural: revenue lost if the supplier stopped for a fixed stress period with
  no help, given inventory (time-to-survive) and whether a qualified alternate
  exists. A Simchi-Levi style stress test, independent of today's weather.
- Exposure: probability the supplier's site goes down in the forecast window.
- Live criticality: expected revenue at risk attributed to that supplier in the
  Monte Carlo propagation (combines both, including joint failures).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .model import Network
from .simulate import SimResult

STRESS_DAYS = 14
EXPOSURE_HIGH = 0.30


@dataclass
class SupplierCriticality:
    supplier: str
    name: str
    estate: str
    parts: list[str]
    time_to_survive_days: float
    has_alternate: bool
    structural_rar_thb: float
    exposure_p_down: float
    median_downtime_days: float
    live_expected_rar_thb: float
    live_p90_rar_thb: float
    quadrant: str

    def to_dict(self) -> dict:
        return asdict(self)


def structural_rar(net: Network, supplier: str, stress_days: int = STRESS_DAYS) -> float:
    """Revenue lost over the horizon if `supplier` stops on day 0 for `stress_days`."""
    total = 0.0
    for prod in net.products.values():
        lost_days = 0.0
        for part in prod.bom:
            for sp in net.supplies:
                if sp.supplier == supplier and sp.part == part and sp.plant == prod.plant:
                    lost_days = max(lost_days, max(0.0, min(stress_days, net.horizon_days) - sp.inventory_days))
        total += lost_days * prod.daily_rate * prod.unit_price_thb
    return total


def assess(net: Network, sim: SimResult) -> list[SupplierCriticality]:
    rows: list[SupplierCriticality] = []
    structural = {s.id: structural_rar(net, s.id) for s in net.suppliers()}
    threshold = sorted(structural.values())[len(structural) // 2] if structural else 0.0
    for s in net.suppliers():
        sps = [sp for sp in net.supplies if sp.supplier == s.id]
        tts = min(sp.inventory_days for sp in sps) if sps else 0.0
        rar = sim.supplier_rar.get(s.id)
        exp_rar = float(rar.mean()) if rar is not None else 0.0
        p90 = float(sorted(rar)[int(0.9 * len(rar))]) if rar is not None else 0.0
        p = sim.site_p_down.get(s.id, 0.0)
        hi_struct = structural[s.id] >= threshold and structural[s.id] > 0
        hi_exp = p >= EXPOSURE_HIGH
        quadrant = {
            (True, True): "act_now",
            (True, False): "build_buffers",
            (False, True): "monitor",
            (False, False): "low",
        }[(hi_struct, hi_exp)]
        rows.append(SupplierCriticality(
            supplier=s.id, name=s.name, estate=s.estate,
            parts=sorted({sp.part for sp in sps}),
            time_to_survive_days=tts,
            has_alternate=any(sp.alternates for sp in sps),
            structural_rar_thb=structural[s.id],
            exposure_p_down=round(p, 3),
            median_downtime_days=round(sim.site_downtime_p50.get(s.id, 0.0), 1),
            live_expected_rar_thb=exp_rar,
            live_p90_rar_thb=p90,
            quadrant=quadrant,
        ))
    rows.sort(key=lambda r: r.live_expected_rar_thb, reverse=True)
    return rows
