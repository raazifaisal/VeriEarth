# VeriEarth — AI Builder Cup build plan (due Sun 18 Oct 2026)

**Product:** live supplier criticality and decision support.
**One-liner:** Know which suppliers matter right now, and what to do about it, from forecasts and satellites rather than supplier declarations.
**Theme:** Manufacturing: Intelligent Operations & Industrial Efficiency.
**Demo event:** Thailand floods, 24–30 Sep 2026.
- Amata City Chonburi zones 7–9 flooded: 34 plants stopped.
- Toyota's disruption began 30 Sep; restart planned 12–14 Oct.
- FTI provisional loss estimate: about 6B baht.
- Sources: nationthailand.com 40071777 and 40071986.

## Verified data the demo stands on
- **Reanalysis rainfall (Open-Meteo archive):**
  - Amata City Chonburi: 88 / 61 / 47 mm on 25–27 Sep.
  - Ban Pho: 88 / 103 / 39 mm.
  - The preceding 10 days averaged about 13 mm a day, so the ground was already wet.
- **Archived forecasts (Open-Meteo previous-runs):**
  - 5 days ahead: about 158 mm for the 3 days at Amata City.
  - 1 day ahead: about 183 mm.
  - This supports the claim "flagged ~5 days ahead".
- **Elevation (Open-Meteo, Copernicus DEM):** Amata City Chonburi is about 5 m.

## Architecture (thin, deployable loop)
```
Next.js /command page  ──►  veri-api (FastAPI, Cloud Run)
                               ├─ engine/ (deterministic, tested)
                               │   hazard · vulnerability · propagation (Monte Carlo)
                               │   criticality (structural × exposure) · planner (OR-Tools)
                               │   emissions (ISO 14083 style) · verifier
                               └─ agents/ (ADK 2.x + Gemini 3.8 Flash)
                                   coordinator → hazard · criticality · planner · verifier · intake · reporter
```
- **Graph:** in-process networkx for the prototype. Neo4j and MCP Toolbox are optional and only added if time allows.
- **Design rule:** Gemini chooses and explains; every number comes from an engine tool and carries its provenance.

## Day-by-day
| Day | Deliverable | Done when |
|---|---|---|
| **Thu 15** | Engine and seed network: seed, hazard, vulnerability, propagation, criticality, planner, emissions, verifier. CLI hindcast. Tests. | `python -m veri.cli hindcast --as-of 2026-09-21` prints a ranked criticality list and a Pareto plan |
| **Fri 16** | ADK agents, intake (multimodal bill of lading → JSON), FastAPI with SSE agent stream | Agent answers "what should I do?" end to end locally with a Gemini key |
| **Sat 17** | `/command` UI: map, 2×2, decision cards, agent panel, approve. Deploy both services to Cloud Run. | Public URL works with no login |
| **Sun 18** | Satellite before/after visual for one site, 3-min video, PDF deck, submit by midday | Submitted |

## Progress (as of Thu 15 Oct, early hours)
- [x] Engine:
  - [x] hazard (real data cached for 18–26 Sep)
  - [x] vulnerability prior
  - [x] Monte Carlo propagation with correlated failures
  - [x] criticality 2×2
  - [x] OR-Tools planner
  - [x] emissions
  - [x] independent verifier
- [x] 10 engine tests pass offline. The verifier catches tampered CO₂ and uncovered shortages.
- [x] Hindcast result, 22 Sep (3 days before the peak):
  - [x] Expected revenue at risk ฿87.5M.
  - [x] Resin supplier ranked "act now".
  - [x] Deciding now costs ฿54.3M with 2.9 t CO₂; deciding after the event costs ฿79.7M with 32 t.
- [x] ADK agent team: coordinator plus 4 specialists, with engine tools. Gemini intake (multimodal, structured output).
- [x] FastAPI service: assessment, plans, verify, adjust, SSE agent chat, intake. Docker image builds and serves.
- [x] Web app (`web/`, Next 15):
  - [x] map, criticality 2×2, decide (timing, plans, live edit + verifier, Pareto), agent chat
  - [x] Observe (Sentinel-1 change) and Intake tabs
- [x] Sentinel-1 observed signal over Amata City:
  - [x] Brightened >3 dB: 10.2% of the area on 27 Sep vs 2.3% on 9 Oct.
  - [x] Production restart was reported 12–14 Oct.
- [x] Sample Thai delivery note for the intake demo: `docs/hackathon/samples/delivery_note_th.png`.
- [x] `deploy.sh` and Cloud Build configs.
- [ ] Live test of agents and intake with a Gemini key.
- [ ] Deploy to Cloud Run.
- [ ] Video, submission deck PDF, submit.

## Blocked on the user (only they can do these)
1. Confirm registration and a 2–4 person team (no students).
2. Rotate the leaked GCP service-account key (git history, commit c341176).
3. Create a Gemini API key in AI Studio and put it in `backend/.env` as `GEMINI_API_KEY=...`.
4. Install the gcloud CLI, run `gcloud auth login`, and pick a project with billing. Enable Run, Cloud Build and Artifact Registry.
5. Optional: request WeatherNext access. Without it, the demo uses the Open-Meteo forecast archive.

## Cut list
- PrefixSpan
- The route×route projection
- AQI
- Redis
- The settings and auth flows for the demo route
- Observed-recovery modelling beyond one illustrative site

## Honesty rules for the demo
- The focal company and its orders are **illustrative**.
- Event dates, rainfall, forecasts and estate locations are **real**. Coordinates are approximate.
- The vulnerability model is a **documented prior**, not a trained model. Say so.
- Emission factors are indicative defaults until GLEC v3 values are loaded.
