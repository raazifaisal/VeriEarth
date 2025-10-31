# Supply Chain Analytics – Business Spec (Org: ecfc141e-2e55-4670-bb8e-9e8813b02866)

## Executive summary
Insights convert graph analytics and EO signals into actions: identify chokepoints, influence hubs, regional cells, greener alternatives, pollution hotspots, corridor legs, and blast radius exposure. Surfaces are decision‑ready, not raw scores.

## Insights and decisions
- Chokepoints (facility betweenness)
  - Why: single‑failure risk; SLA exposure.
  - Show: rank, score, impacted flow share, top counterparties.
  - Act: dual‑sourcing, buffers, alternates.
- Influence hubs (facility PageRank)
  - Why: disruption propagates widely.
  - Show: score, in/out degree, reach.
  - Act: monitoring, reliability contracts.
- Regional cells (facility Louvain)
  - Why: cluster‑level optimization.
  - Show: community id/size, members, mode mix.
  - Act: consolidation, pooled inventory.
- Greener/faster alternatives (shortest path)
  - Why: abatement with SLA guardrails.
  - Show: baseline vs alt by distance/duration/emission.
  - Act: route swaps, scheduling.
- Pollution hotspots (EO overlay, AQI)
  - Why: workforce/community risk.
  - Show: latest AQI, 3‑month trend.
  - Act: shift changes, mitigation engagement.
- Exposure degree (in/out/total)
  - Why: load balance targets.
  - Show: deg metrics, flow share.
  - Act: redistribution, windowing.
- Blast radius (1–2 hops)
  - Why: incident scope.
  - Show: neighbors by hop, alternates.
  - Act: response plans.
- Corridor legs (route PageRank)
  - Why: lane importance.
  - Show: PR score, mode, km, adjacent facilities.
  - Act: carrier SLAs, emission factor improvements.
- Bridge legs (route betweenness)
  - Why: cluster bridges.
  - Show: score, alternates.
  - Act: redundancy programs.
- Data/graph health
  - Why: confidence & freshness.
  - Show: node/edge counts, builtAt, EO coverage.
  - Act: rebuild/backfill.

## KPIs (by surface)
- Betweenness: score, %paths impacted, top counterparties.
- PageRank: score, in/out degree, unique reach.
- Louvain: community id, size, intra‑cluster share, mode mix.
- Shortest path: total cost, legs, delta emission/duration.
- EO: latest AQI, trend(3m).
- Degree: inDeg, outDeg, total.
- Neighbors: counts by hop, alternates presence.
- Route PR/Bet: score, adjacent facilities, lane stats.
- Health: nodeCount, relationshipCount, builtAt; EO min/max/rows.

## Thresholds (defaults)
- AQI hotspot: ≥100; trend spike: +10 over 3m.
- High betweenness/PageRank: top 10% of facilities.
- Emission win: ≥10% reduction, duration penalty ≤15%.
- Stale projection: >24h or post data change.

## API contract (org‑scoped)
- GET /api/kg/analytics/facilities/betweenness
  - q: org_id, limit
  - r: [{facilityId, score, impactShare, topCounterparties[]}]
- GET /api/kg/analytics/facilities/pagerank
  - q: org_id, limit
  - r: [{facilityId, score, inDeg, outDeg, reach}]
- GET /api/kg/analytics/facilities/communities
  - q: org_id
  - r: [{communityId, size, members[], modeMix}]
- GET /api/kg/analytics/facilities/degree
  - q: org_id, limit
  - r: [{facilityId, inDeg, outDeg, totalDeg}]
- POST /api/kg/analytics/shortest-path
  - b: {org_id, srcNode, dstNode, weight:'distance'|'duration'|'emission'}
  - r: {weight, totalCost, facilityIds[], legs:[{originId,destId,km,hours,emissionWeight}]}
- POST /api/kg/analytics/compare-paths
  - b: {org_id, srcNode, dstNode}
  - r: {distancePath, durationPath, emissionPath, deltas}
- GET /api/kg/analytics/routes/pagerank
  - q: org_id, limit
  - r: [{routeId, mode, km, score}]
- GET /api/kg/analytics/routes/betweenness
  - q: org_id, limit
  - r: [{routeId, score, bridgesClusters}]
- GET /api/kg/analytics/neighbors
  - q: org_id, facility_id, hops(1|2)
  - r: {nodes[], edges[]}
- GET /api/kg/eo/hotspots
  - q: org_id, limit
  - r: [{facilityId, observed_at, aqi, trend3m}]
- GET /api/kg/eo/coverage
  - q: org_id
  - r: [{facilityId, rows, min_ts, max_ts, hasGaps}]
- POST /api/kg/graphs/build
  - b: {org_id}
  - r: {built:[{name,nodeCount,relationshipCount}], builtAt}
- GET /api/kg/graphs/status
  - q: org_id
  - r: {graphs:[{name,nodeCount,relationshipCount,builtAt}]}

## Response shapes
- FacilityInsight: facilityId, name?, city?, score, percentile, tags[], topRoutes[], trend.
- RouteInsight: routeId, mode, km, score, adjacentFacilities[], laneRiskTag.
- PathCompare: weight, totalCost, facilityIds[], legs[].

## Frontend UX (per surface)
- Cards: headline + action (View alternates, Simulate swap, Create watch).
- Tables: entity, score, context, trends, updatedAt.
- Badges: High risk, AQI hotspot, Data gap, Stale projection.
- Tooltips: plain definitions (betweenness, PageRank, Louvain, AQI, emission‑weight).

## Ops
- Build graphs after KG sync or on demand; cache top‑N for 30–60 min.
- Invalidate on ingestion changes or explicit rebuild.
- Include projection timestamp for freshness badges.

## References
- Neo4j Graph Data Science – Algorithms and projections: https://neo4j.com/docs/graph-data-science/current/algorithms/
