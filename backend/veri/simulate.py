"""Monte Carlo propagation: correlated site failures -> part shortages -> lost production -> late orders.

Each scenario:
1. picks a lagged-ensemble forecast member and a shared regional rain multiplier
   (one storm hits many sites at once);
2. draws each site's failure through a Gaussian copula with region and estate
   factors, so nearby sites fail together;
3. draws time-to-recover for failed sites;
4. turns supplier outages into part shortage days after inventory runs out
   (time-to-survive vs time-to-recover, after Simchi-Levi et al. 2015);
5. turns shortages into lost production days per product and late orders.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

from .hazard import HazardSnapshot, SiteHazard
from .model import Network
from .vulnerability import DOWNTIME_SIGMA, p_down_and_median_vec

REGION_RAIN_SIGMA = 0.25   # shared multiplicative forecast error
LOCAL_RAIN_SIGMA = 0.15    # site-level rain variability
W_REGION, W_ESTATE = 0.6, 0.5  # copula loadings; remainder is idiosyncratic


@dataclass
class SimResult:
    n: int
    horizon: int
    site_p_down: dict[str, float]
    site_downtime_p50: dict[str, float]
    site_event_day: dict[str, int]
    part_shortage_days: dict[tuple[str, str], np.ndarray]   # (part, plant) -> per-scenario days
    product_lost_days: dict[str, np.ndarray]
    revenue_at_risk: np.ndarray                              # per scenario, THB
    supplier_rar: dict[str, np.ndarray]                      # attributed per scenario
    order_p_late: dict[str, float]
    joint_down: dict[tuple[str, str], float] = field(default_factory=dict)

    def summary(self) -> dict:
        r = self.revenue_at_risk
        return {
            "scenarios": self.n,
            "expected_revenue_at_risk_thb": float(r.mean()),
            "p50_thb": float(np.percentile(r, 50)),
            "p90_thb": float(np.percentile(r, 90)),
            "p_any_loss": float((r > 0).mean()),
        }


def _estate_key(est: str) -> str:
    return est.split("(")[0].strip()


def _event_day(h: SiteHazard, member: int) -> int:
    """Day index (0-based, relative to as_of+1) when the 3-day rain peak starts."""
    s = h.forecast_daily_mm[member]
    sums = [sum(s[i:i + 3]) for i in range(max(1, len(s) - 2))]
    return int(np.argmax(sums))


def run(net: Network, snap: HazardSnapshot, n: int = 4000, seed: int = 7) -> SimResult:
    rng = np.random.default_rng(seed)
    H = net.horizon_days
    sites = [s for s in net.sites.values() if s.id in snap.sites]
    ids = [s.id for s in sites]
    idx = {sid: i for i, sid in enumerate(ids)}
    estates = sorted({_estate_key(s.estate) for s in sites})
    est_idx = np.array([estates.index(_estate_key(s.estate)) for s in sites])
    n_members = len(next(iter(snap.sites.values())).forecast_daily_mm)

    member = rng.integers(0, n_members, size=n)
    region_mult = np.exp(rng.normal(0, REGION_RAIN_SIGMA, size=n))
    local_mult = np.exp(rng.normal(0, LOCAL_RAIN_SIGMA, size=(n, len(ids))))

    # Failure probability per scenario and site.
    p = np.zeros((n, len(ids)))
    med = np.zeros((n, len(ids)))
    event_day = np.zeros((n, len(ids)), dtype=int)
    for j, sid in enumerate(ids):
        h = snap.sites[sid]
        r3 = np.array([h.max_3day(m) for m in h.forecast_daily_mm])
        ev = np.array([_event_day(h, m) for m in range(n_members)])
        rain = r3[member] * region_mult * local_mult[:, j]
        p[:, j], med[:, j] = p_down_and_median_vec(rain, h.antecedent_mm, h.elevation_m)
        event_day[:, j] = ev[member]

    # Gaussian copula: shared region and estate factors make nearby sites fail together.
    z_region = rng.normal(size=(n, 1))
    z_estate = rng.normal(size=(n, len(estates)))[:, est_idx]
    w_id = np.sqrt(max(1e-9, 1 - W_REGION ** 2 - W_ESTATE ** 2))
    latent = W_REGION * z_region + W_ESTATE * z_estate + w_id * rng.normal(size=(n, len(ids)))
    down = norm.cdf(latent) < p
    ttr = np.where(down, med * np.exp(rng.normal(0, DOWNTIME_SIGMA, size=(n, len(ids)))), 0.0)

    # Part shortages at each plant (time-to-recover minus time-to-survive).
    days = np.arange(H)
    short_mask: dict[tuple[str, str], np.ndarray] = {}
    shortage_days: dict[tuple[str, str], np.ndarray] = {}
    supplier_of: dict[tuple[str, str], str] = {}
    for sp in net.supplies:
        j = idx.get(sp.supplier)
        key = (sp.part, sp.plant)
        supplier_of[key] = sp.supplier
        if j is None:
            mask = np.zeros((n, H), dtype=bool)
        else:
            start = event_day[:, j] + sp.inventory_days
            end = event_day[:, j] + ttr[:, j]
            mask = (days[None, :] >= start[:, None]) & (days[None, :] < end[:, None]) & down[:, [j]]
        short_mask[key] = mask
        shortage_days[key] = mask.sum(axis=1)

    # Lost production per product: any BOM part short stops the line that day.
    product_lost: dict[str, np.ndarray] = {}
    rar = np.zeros(n)
    supplier_rar = {s: np.zeros(n) for s in {sp.supplier for sp in net.supplies}}
    order_late = {o.id: np.zeros(n, dtype=bool) for o in net.orders}
    for prod in net.products.values():
        masks = [short_mask[(part, prod.plant)] for part in prod.bom]
        stacked = np.stack(masks)                       # parts x n x H
        lost = stacked.any(axis=0)                      # n x H
        product_lost[prod.id] = lost.sum(axis=1)
        daily_value = prod.daily_rate * prod.unit_price_thb
        rar += product_lost[prod.id] * daily_value
        # Attribute each lost day equally to the suppliers whose parts were short.
        n_short = np.maximum(stacked.sum(axis=0), 1)
        for part, m in zip(prod.bom, masks):
            supplier_rar[supplier_of[(part, prod.plant)]] += (m / n_short).sum(axis=1) * daily_value
        # Orders: FIFO against cumulative production.
        prod_orders = sorted((o for o in net.orders if o.product == prod.id), key=lambda o: o.due_offset_days)
        made = np.cumsum(np.where(lost, 0.0, prod.daily_rate), axis=1)
        cum_due = 0.0
        for o in prod_orders:
            cum_due += o.qty
            d = min(o.due_offset_days, H) - 1
            order_late[o.id] = made[:, d] < cum_due - 1e-6

    joint = {}
    for sp in net.supplies:
        for alt in sp.alternates:
            if sp.supplier in idx and alt in idx:
                joint[(sp.supplier, alt)] = float((down[:, idx[sp.supplier]] & down[:, idx[alt]]).mean())

    return SimResult(
        n=n, horizon=H,
        site_p_down={sid: float(down[:, j].mean()) for sid, j in idx.items()},
        site_downtime_p50={sid: float(np.median(ttr[down[:, j], j])) if down[:, j].any() else 0.0 for sid, j in idx.items()},
        site_event_day={sid: int(np.median(event_day[:, j])) for sid, j in idx.items()},
        part_shortage_days=shortage_days,
        product_lost_days=product_lost,
        revenue_at_risk=rar,
        supplier_rar=supplier_rar,
        order_p_late={k: float(v.mean()) for k, v in order_late.items()},
        joint_down=joint,
    )
