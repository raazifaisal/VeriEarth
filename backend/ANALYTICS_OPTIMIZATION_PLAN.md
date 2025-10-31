## Analytics and Optimization Plan (GDS + PrefixSpan + Min‑Cost Flow)

USE EMISSION FACTORS 

### 1) Purpose
Unify graph analytics (GDS), advanced sequence mining (PrefixSpan/CM‑SPAM), and optimization (knapsack/min‑cost flow) to identify “hidden heavy hitters” and re‑route or mode‑swap flows to reduce organization‑level emissions while respecting service and capacity constraints.

### 2) Scope and Fit in VeriEarth
- Source of truth: PostgreSQL (Suppliers, Facilities, Routes, Shipments, Products/POs), EO snapshots in `EOReading`.
- Knowledge Graph: Neo4j (single DB; multi‑tenant via `org_id`).
- This module exposes analytics/optimization APIs that the frontend can trigger from the KG page (Analytics tabs) and Data Management/Enrichment screens.

### 3) Data Model (minimum required)
- Facilities: id, org_id, name, type, geo, optional city/state.
- Routes (node): id, org_id, transport_mode, distance_km, duration_hours; relationships `(:Facility)-[:ORIGIN]->(:Route)-[:DESTINATION]->(:Facility)`.
- Shipments (optional but preferred): id, org_id, route_id, shipment_date (to infer frequency).
- EO (latest snapshot per facility): NO2, SO2, O3, AER_AI, CO, HCHO; plus an EO composite proxy if available.

Derived/auxiliary
- Emission factors by mode (tonne‑km factors or simple per‑km fallback).
- Capacity constraints per mode (rough defaults allowed).
- SLA thresholds (max additional duration vs baseline).

### 4) Analytics Pillar A: Neo4j GDS (graph‑native)
Goals: structural risk and alternates.

- Facility Graph Projection (org‑scoped): collapse `Route` nodes into edges or keep bipartite projection; store relationship weights `distance`, `duration`, and optional `emission_weight`.
- Core analytics:
  - Shortest path: Dijkstra on `distance`/`duration`/`emission_weight` (what‑if view).
  - Betweenness/PageRank (facilities): “bridges” and “hubs”.
  - Route importance: PageRank on Route→Route (shared facility) graph.
  - Communities: Louvain (facility clusters) for localized interventions.

Inputs
- org_id, weight key, source/target facility ids (for paths).

Outputs (examples)
- Paths: `[facility_id...]`, totalCost.
- Rankings: list of `{entity_id, name, score}`.

Operational notes
- Maintain per‑org named projections (drop/rebuild on sync).
- Add unique constraints and useful indexes as already defined in `kg_routes.py`.

### 5) Analytics Pillar B: Advanced Sequence Mining (PrefixSpan/CM‑SPAM)
Goals: surface recurring emission‑heavy chains missed by single‑path views.

Event building (per org)
- Construct sequences of steps: `Supplier → mode → Warehouse [→ mode → Retail]` by joining legs sharing a warehouse (or multi‑leg where present).
- Weight per event (emission_per_tx) = route emissions + EO proxies for facilities involved.
- Optional pollutant_index_tx = normalized composite of NO2, SO2, O3, AER_AI, CO, HCHO (weights tunable).
- Frequency proxy: shipments; fallback to route frequency or PO volume.

Mining
- PrefixSpan at min_support ≈ 0.5–1% of events (absolute floor 25), max pattern length 5 tokens.
- Optionally SPADE/CM‑SPAM via SPMF for speed on dense data.

Outputs per pattern
- `sequence` (human‑readable), `pattern` (tokens), `support_count`, `emission_sum`, `emission_avg`, optional `pollutant_sum`.

Peer‑normalized anomalies
- Peer groups by leg count and mode signature; compute median/MAD of `emission_avg`, report `robust_z` and `excess_vs_peer` for fairness.

Scheduling/caching
- Run post‑ingestion or nightly and cache top‑K results per org (immediate UI load).

### 6) Optimization Pillar: From insights to abatement
Two levels:

Level 1 — Pattern‑level knapsack (quick wins)
- Decision unit: apply an intervention to pattern P’s leg L (e.g., truck→rail) for all occurrences.
- Value: `support_count(P) × (emission_avg_current − emission_avg_alt)`.
- Cost: estimated capex/opex uplift or penalty.
- Constraint: budget, max number of changes, SLA (exclude candidates increasing duration beyond threshold).
- Solve: 0/1 knapsack (greedy or ILP via OR‑Tools/PuLP).

Level 2 — Network min‑cost flow (deeper re‑routing)
- Build facility graph with demand (OD pairs, or infer from sequences) and candidate edges with costs = `emission_weight` (or convex blend with opex), capacities, and travel time.
- Objective: minimize total emission cost while meeting demand and respecting capacities and SLA.
- Solve: min‑cost flow (successive shortest path) or LP.

Inputs
- Emission factors by mode, alt path catalogs from GDS shortest paths, capacity and SLA constraints, demand volumes.

Outputs
- Selected interventions (knapsack) or reassigned flows (min‑cost flow): delta‑CO2e, cost, affected nodes/routes, SLA deltas.

### 7) API Surfaces (draft)
GDS
- `POST /api/kg/analytics/shortest-path` → {path, totalCost}
- `GET  /api/kg/analytics/centrality/betweenness` → [{facilityId, score}]
- `GET  /api/kg/analytics/communities/louvain` → [{facilityId, communityId}]
- `GET  /api/kg/analytics/routes/pagerank` → [{routeId, score}]

Sequences
- `POST /api/kg/analytics/sequences/prefixspan` → [{sequence, support_count, emission_sum, emission_avg, pollutant_sum?}]
- `GET  /api/kg/analytics/outliers/peer` → [{sequence, robust_z, excess_vs_peer, support_count}]
- `GET  /api/kg/analytics/lastmile` → [{wr_leg, support_count, emission_sum}]

Optimization
- `POST /api/kg/opt/knapsack` → [{intervention, delta_tco2e, est_cost, roi}]
- `POST /api/kg/opt/mincostflow/simulate` → {flows_before, flows_after, delta_tco2e, sla_impacts}

All endpoints are org‑scoped and require org sudo authorization for prescriptive “apply” actions.

### 8) Frontend Integration (KG page)
- Tabs: “Graph Analytics” and “Advanced Mining”.
- Graph Analytics: top lists (critical facilities/routes), communities overlay, path compare (distance vs duration vs emission), fit/re‑layout on result.
- Advanced Mining: two tables (by emission_sum vs by support), scatter (support vs emission_sum), peer‑normalized outliers, last‑mile legs.
- Optimization: “Propose Interventions” panel listing top candidates with estimated reduction and SLA/cost flags; export as CSV; optional “simulate” button.

### 9) Metrics & Ops
- Accuracy: spot‑check mined sequences vs raw shipments; validate EO proxies cadence.
- Performance: cache per‑org results; use batched GDS; set timeouts.
- Governance/Security: org_id filters in all queries; sudo password for destructive or prescriptive ops.
- Observability: store run timestamps, parameters, counts in a simple analytics_runs table.

### 10) Benefits
- Structural + behavioral view: GDS highlights topology risk; sequences expose recurring impact.
- Actionability: concrete mode swaps and reroutes with estimated reductions.
- Tenant isolation: org‑scoped projections and caches.
- Extensible: can add cost and reliability into multi‑objective optimization later.

### 11) Limitations / Assumptions
- Neo4j Community single DB; isolation via `org_id` only.
- Sequence mining outside GDS; run batch, not real‑time.
- EO proxies are relative indicators; not stack measurements.
- Emission factors and capacities may be coarse; require iteration with client data.

### 12) Phased Rollout
- Phase A (now): GDS endpoints, sequence mining batch, cached top‑K, UI readouts.
- Phase B: Knapsack quick‑wins with SLA filters; CSV export of recommendations.
- Phase C: Min‑cost flow simulator; compare baseline vs optimized; add budget/capacity inputs.
- Phase D: Feedback loop (apply changes to route prefs) and delta tracking over time.

### 13) Inputs/Outputs Summary
- Inputs: org_id; facility/route/shipments from PG; EO snapshots; emission factors; SLA/capacity.
- Outputs: ranked nodes/routes; mined sequences with support/emissions; outlier list; intervention set or flow reassignments with delta‑CO2e and SLA impact.

---
Questions to confirm
- EO proxy: latest snapshot vs monthly rollup?
- Initial min_support and top‑K counts?
- SLA tolerance (max additional duration) and crude capacity by mode?


