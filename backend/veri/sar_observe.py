"""Observed disruption from Sentinel-1 radar: same-orbit change detection over an estate.

Flooded built-up areas often get BRIGHTER in C-band radar (double bounce between
water and walls), which is why simple dark-water thresholds miss industrial-estate
floods. We measure the share of the area brightening by >3 dB against a pre-event
reference from the same orbit, after a 5x5 boxcar speckle filter, and render
overlays for the UI.

Data: Sentinel-1 RTC via Microsoft Planetary Computer (public STAC, no key).

    python -m veri.sar_observe --out ../web/public/sat
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import httpx
import numpy as np

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
DATA = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{bbox}.tif"
BBOX = (100.985, 13.385, 101.075, 13.465)  # Amata City Chonburi and surroundings (approximate)
POINT = (101.025, 13.425)
WINDOW = "2026-09-10T00:00:00Z/2026-10-14T23:59:59Z"
PAIRS = {"asc": ("20260915", ["20260927", "20261009"]), "desc": ("20260919", ["20261001"])}
THRESH_DB = 3.0


def _scenes(client: httpx.Client) -> dict[str, str]:
    r = client.post(STAC, json={"collections": ["sentinel-1-rtc"], "limit": 50, "datetime": WINDOW,
                                "intersects": {"type": "Point", "coordinates": list(POINT)}})
    return {f["properties"]["datetime"][:10].replace("-", ""): f["id"] for f in r.json()["features"]}


def _db(client: httpx.Client, item: str):
    import tifffile
    from scipy.ndimage import uniform_filter

    url = DATA.format(bbox=",".join(map(str, BBOX)))
    r = client.get(url, params={"collection": "sentinel-1-rtc", "item": item, "assets": "vv", "max_size": 900})
    r.raise_for_status()
    a = tifffile.imread(io.BytesIO(r.content))[..., 0].astype(np.float32)
    return 10 * np.log10(uniform_filter(np.clip(a, 1e-4, None), size=5))


def _overlay(base, mask, path: Path) -> None:
    from PIL import Image

    g = (np.clip((base + 20) / 24, 0, 1) * 255).astype(np.float32)
    rgb = np.dstack([g, g, g]) * 0.85
    rgb[mask] = 0.25 * rgb[mask] + 0.75 * np.array([217, 98, 43])
    Image.fromarray(rgb.astype(np.uint8)).save(path)


def run(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    stats = {}
    with httpx.Client(timeout=180) as c:
        ids = _scenes(c)
        for geom, (ref, others) in PAIRS.items():
            r = _db(c, ids[ref])
            _overlay(r, np.zeros_like(r, bool), out / f"sar_{geom}_{ref}.png")
            for d in others:
                diff = _db(c, ids[d]) - r
                m = diff > THRESH_DB
                stats[f"{geom}:{ref}->{d}"] = {"brightened_gt3db": round(float(m.mean()), 3),
                                               "darkened_gt3db": round(float((diff < -THRESH_DB).mean()), 3)}
                _overlay(r, m, out / f"sar_{geom}_{d}_change.png")
    meta = {"bbox": BBOX, "threshold_db": THRESH_DB, "stats": stats,
            "source": "Sentinel-1 RTC (Microsoft Planetary Computer), VV, 5x5 boxcar, change vs same-orbit reference"}
    (out / "sar_stats.json").write_text(json.dumps(meta, indent=1))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../web/public/sat")
    print(json.dumps(run(Path(ap.parse_args().out)), indent=1))
