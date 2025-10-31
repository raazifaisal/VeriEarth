# Analytics MVP Spec (Org: ecfc141e-2e55-4670-bb8e-9e8813b02866)

## Scope (now)
- Chokepoints (facility betweenness)
- Influence hubs (facility PageRank)
- Regional cells (facility Louvain)
- Path compare (distance | duration | emission)
- EO hotspots (latest AQI + 3m trend)
- Graph status (node/edge counts; builtAt)
- Route insights (PageRank, Betweenness, Communities)

## Endpoints
- GET /api/kg/analytics/facilities/betweenness?org_id=…&limit=15
  - r: [{facilityId, score, impactShare?}]
- GET /api/kg/analytics/facilities/pagerank?org_id=…&limit=15
  - r: [{facilityId, score, inDeg?, outDeg?}]
- GET /api/kg/analytics/facilities/communities?org_id=…
  - r: [{communityId, size, members}]
- GET /api/kg/analytics/routes/pagerank?org_id=…&limit=15
  - r: [{routeId, score}]
- GET /api/kg/analytics/routes/betweenness?org_id=…&limit=15
  - r: [{routeId, score}]
- GET /api/kg/analytics/routes/communities?org_id=…
  - r: [{communityId, size, members}]
- POST /api/kg/analytics/shortest-path
  - b: {org_id, srcNode, dstNode, weight}
  - r: {weight, totalCost, facilityIds, legs}
- GET /api/kg/eo/hotspots?org_id=…&limit=20
  - r: [{facilityId, observed_at, aqi, trend3m}]
- GET /api/kg/graphs/status?org_id=…
  - r: {graphs:[{name,nodeCount,relationshipCount,builtAt}]}
- POST /api/kg/graphs/build
  - b: {org_id}
  - r: {built:[{name,nodeCount,relationshipCount}], builtAt}

## Payload shapes
- FacilityScore: {facilityId, score, rank?}
- Community: {communityId, size, members:[id]}
- RouteScore: {routeId, score}
- PathCompare: {weight, totalCost, facilityIds:[id], legs:[{originId,destId,km,hours,emissionWeight}]}
- EOHotspot: {facilityId, observed_at, aqi, trend3m}
- GraphStatus: {name, nodeCount, relationshipCount, builtAt}

## UI (minimal)
- Cards (top):
  - Chokepoints: top 5 (facilityId, score)
  - Hubs: top 5 (facilityId, score)
  - Hotspots: top 5 (facilityId, aqi)
- Tables:
  - Communities (id, size, sample members)
  - Route insights (PageRank/Betweenness top 10)
  - Paths (compare form + results table)
- Badges: High risk (top 10%), AQI≥100, Stale graph (>24h)
- Tooltips: one‑liners (betweenness = chokepoint risk; PageRank = influence)
- For richer business copy and call‑outs, see `ANALYTICS_BUSINESS_SPEC.md`.

## Defaults/thresholds
- High risk: top 10% by score
- AQI hotspot: ≥100; trend spike ≥+10 over 3m
- Emission win: ≥10% with ≤15% duration penalty
- Stale graph: >24h since builtAt

## Ops
- Build facility + route graphs on demand (POST /build) or nightly
- Cache analytics for 30 min per org
- Invalidate on ingestion sync or explicit rebuild

## Notes
- Start with facility analytics in UI; surface route leaderboards alongside
- Keep responses small (limit 15) and add pagination later
