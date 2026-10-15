"""Hazard inputs per site, as they would have been known on an `as_of` date.

Sources (no API key needed, cached to disk so demos are reproducible):
- Observed rainfall: Open-Meteo historical archive (reanalysis).
- Forecast rainfall: Open-Meteo previous-runs API. For a target date t, the
  forecast issued k days earlier is `precipitation_previous_day{k}`. Forecasts
  issued on as_of, as_of-1 and as_of-2 form a lagged ensemble (3 members).
- Elevation: Open-Meteo elevation API (Copernicus DEM, 90 m).

Earth Engine / WeatherNext can replace these behind the same interface.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx

from .model import DATA_DIR, Network, Site

CACHE_DIR = DATA_DIR / "hazard_cache"
TZ = "Asia/Bangkok"
LEAD_DAYS = 7          # previous-runs API offers previous_day1..7
LAGS = (0, 1, 2)       # lagged-ensemble members: issued as_of, as_of-1, as_of-2
ANTECEDENT_DAYS = 14

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PREV_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ELEV_URL = "https://api.open-meteo.com/v1/elevation"


@dataclass
class SiteHazard:
    site_id: str
    elevation_m: float
    antecedent_mm: float                 # observed rain in the 14 days before as_of
    forecast_daily_mm: list[list[float]]  # [member][day 1..LEAD_DAYS]
    observed_daily_mm: list[float]       # what actually fell, days 1..LEAD_DAYS (hindcast check)

    def max_3day(self, series: list[float]) -> float:
        return max((sum(series[i:i + 3]) for i in range(max(1, len(series) - 2))), default=0.0)

    @property
    def forecast_max3_by_member(self) -> list[float]:
        return [self.max_3day(m) for m in self.forecast_daily_mm]

    @property
    def observed_max3(self) -> float:
        return self.max_3day(self.observed_daily_mm)


@dataclass
class HazardSnapshot:
    as_of: str
    source: str
    sites: dict[str, SiteHazard]

    def to_json(self) -> str:
        return json.dumps({"as_of": self.as_of, "source": self.source,
                           "sites": {k: asdict(v) for k, v in self.sites.items()}}, indent=1)

    @staticmethod
    def from_json(text: str) -> "HazardSnapshot":
        raw = json.loads(text)
        return HazardSnapshot(raw["as_of"], raw["source"], {k: SiteHazard(**v) for k, v in raw["sites"].items()})


def _iso(d: date) -> str:
    return d.isoformat()


def _daily_sums(times: list[str], values: list[float | None]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for t, v in zip(times, values):
        out[t[:10]] += v or 0.0
    return out


def _as_list(resp_json) -> list[dict]:
    return resp_json if isinstance(resp_json, list) else [resp_json]


def fetch_snapshot(net: Network, as_of: date, client: httpx.Client | None = None) -> HazardSnapshot:
    """Fetch hazard inputs for every non-overseas site, batched in single requests."""
    sites = [s for s in net.sites.values() if not s.overseas]
    lats = ",".join(f"{s.lat:.4f}" for s in sites)
    lons = ",".join(f"{s.lon:.4f}" for s in sites)
    own = client is None
    client = client or httpx.Client(timeout=60)
    try:
        elev = client.get(ELEV_URL, params={"latitude": lats, "longitude": lons}).json()["elevation"]

        ante = _as_list(client.get(ARCHIVE_URL, params={
            "latitude": lats, "longitude": lons, "timezone": TZ, "daily": "precipitation_sum",
            "start_date": _iso(as_of - timedelta(days=ANTECEDENT_DAYS)), "end_date": _iso(as_of - timedelta(days=1)),
        }).json())

        targets = [as_of + timedelta(days=k) for k in range(1, LEAD_DAYS + 1)]
        obs = _as_list(client.get(ARCHIVE_URL, params={
            "latitude": lats, "longitude": lons, "timezone": TZ, "daily": "precipitation_sum",
            "start_date": _iso(targets[0]), "end_date": _iso(targets[-1]),
        }).json())

        lead_vars = ",".join(f"precipitation_previous_day{k}" for k in range(1, LEAD_DAYS + 1))
        prev = _as_list(client.get(PREV_RUNS_URL, params={
            "latitude": lats, "longitude": lons, "timezone": TZ, "hourly": lead_vars,
            "start_date": _iso(targets[0]), "end_date": _iso(targets[-1]),
        }).json())
    finally:
        if own:
            client.close()

    result: dict[str, SiteHazard] = {}
    for i, s in enumerate(sites):
        hourly = prev[i]["hourly"]
        daily_by_lead = {k: _daily_sums(hourly["time"], hourly[f"precipitation_previous_day{k}"])
                         for k in range(1, LEAD_DAYS + 1)}
        members = []
        for lag in LAGS:
            series = []
            for j, t in enumerate(targets, start=1):
                # Older runs don't reach the far end of the window; fall back to the
                # longest lead that does (the archive keeps previous_day1..7 only).
                k = min(j + lag, LEAD_DAYS)
                series.append(round(daily_by_lead[k].get(_iso(t), 0.0), 1))
            members.append(series)
        result[s.id] = SiteHazard(
            site_id=s.id,
            elevation_m=float(elev[i]),
            antecedent_mm=round(sum(v or 0.0 for v in ante[i]["daily"]["precipitation_sum"]), 1),
            forecast_daily_mm=members,
            observed_daily_mm=[round(v or 0.0, 1) for v in obs[i]["daily"]["precipitation_sum"]],
        )
    return HazardSnapshot(_iso(as_of), "open-meteo: archive + previous-runs + elevation", result)


def load_or_fetch(net: Network, as_of: date, refresh: bool = False) -> HazardSnapshot:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_iso(as_of)}.json"
    if path.exists() and not refresh:
        snap = HazardSnapshot.from_json(path.read_text(encoding="utf-8"))
        if all(s.id in snap.sites for s in net.sites.values() if not s.overseas):
            return snap
    snap = fetch_snapshot(net, as_of)
    path.write_text(snap.to_json(), encoding="utf-8")
    return snap


def overseas_site(site: Site) -> bool:
    return site.overseas
