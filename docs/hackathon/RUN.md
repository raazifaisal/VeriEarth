# Running VeriEarth (criticality build)

## Local
```bash
# API (Python 3.11)
cd backend
uv venv .venv-veri --python 3.11
uv pip install --python .venv-veri -r requirements-veri.txt
echo "GEMINI_API_KEY=..." > .env           # optional: agent + intake need it
.venv-veri/Scripts/python -m uvicorn veri_app:app --port 8080

# Web (Node 20+)
cd web
npm ci
npm run build && npm start                 # http://localhost:3000
```

Deep links: `/?date=2026-09-22&tab=Decide&site=S-RESIN`. Tabs: Criticality, Decide, Agent, Observe, Intake.

## Checks
```bash
cd backend
.venv-veri/Scripts/python -m pytest tests_veri -q                    # engine tests, offline
.venv-veri/Scripts/python -m veri.cli hindcast --as-of 2026-09-22    # console hindcast
```

## Data refresh (needs network)
- Hazard snapshots are cached in `backend/veri/data/hazard_cache/`. A new date fetches automatically on first use.
- Regenerate the radar visuals and stats with `python -m veri.sar_observe --out ../web/public/sat`. This needs Pillow and tifffile installed in the venv.

## Deploy (Cloud Run)
```bash
gcloud auth login
export PROJECT=<project-id> GEMINI_API_KEY=<key>
bash deploy.sh        # builds both images with Cloud Build, deploys to asia-southeast1, prints URLs
```

## What is real vs illustrative
| Real | Illustrative |
|---|---|
| Event dates and reported impacts (nationthailand.com, 8 Oct 2026) | Focal company Siam Interior Components, supplier names |
| Observed rain and elevation (Open-Meteo archive / elevation) | Inventory days, prices, orders, alternate terms |
| Archived forecast runs (Open-Meteo previous-runs) | Vulnerability coefficients (documented prior) |
| Sentinel-1 radar change (Planetary Computer) | Emission factors (indicative WTW defaults) |
| Estate and OEM plant locations (approximate) | |
