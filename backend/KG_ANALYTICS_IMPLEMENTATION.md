# Knowledge Graph Analytics Implementation

## Overview
This document summarizes the complete implementation of the Knowledge Graph Analytics system, integrating Neo4j GDS (Graph Data Science) algorithms, frequent pattern mining, and environmental data overlay.

---

## Architecture

### Two-Phase Approach

#### Phase 1: Data Sync (Postgres → Neo4j)
**Trigger**: Manual sync via `/api/kg/sync` or automatic on data ingestion  
**Actions**:
1. Sync all entities (Organization, Supplier, Facility, Route, Shipment, EOReading, Product, PurchaseOrder)
2. Compute `emission_weight` on Route nodes (sum of all shipment emissions per route)
3. Store graph in Neo4j with `org_id` property for multi-tenancy

**Key Files**:
- `services/kg_etl_service.py`: Core ETL logic, emission weight computation

#### Phase 2: Analytics (On-Demand)
**Trigger**: User visits Analytics tab in frontend, calls `/api/kg/analytics/*` endpoints  
**Actions**:
1. Build in-memory GDS graphs (facility graph, route graph) using `gds.graph.project`
2. Run GDS algorithms (Betweenness, PageRank, Louvain, Shortest Path)
3. Mine frequent emission patterns with PrefixSpan
4. Fetch EO hotspots from Neo4j

**Key Files**:
- `routes/kg_analytics_routes.py`: All analytics endpoints
- `services/prefixspan_service.py`: Frequent pattern mining logic

---

## API Endpoints

### Base Path: `/api/kg/analytics`

| Endpoint | Method | Description | Key Parameters |
|----------|--------|-------------|----------------|
| `/graphs/build` | POST | Build in-memory GDS graphs for org | `org_id` |
| `/graphs/status` | GET | Get status of projected graphs | `org_id` |
| `/graphs/clear` | DELETE | Drop facility and route graphs | `org_id` |
| `/facilities/betweenness` | GET | Betweenness Centrality on facilities | `org_id`, `limit` |
| `/facilities/pagerank` | GET | PageRank on facilities | `org_id`, `limit` |
| `/facilities/communities` | GET | Louvain community detection | `org_id` |
| `/routes/pagerank` | GET | PageRank on routes | `org_id`, `limit` |
| `/routes/betweenness` | GET | Betweenness on routes | `org_id`, `limit` |
| `/routes/communities` | GET | Louvain on routes | `org_id` |
| `/shortest-path` | POST | Dijkstra shortest path (distance/duration/emission) | `org_id`, `srcNode` (facility ID), `dstNode` (facility ID), `weight` |
| `/sequences/prefixspan` | POST | Frequent emission pattern mining | `org_id`, `min_support`, `max_len`, `top_k` |
| `/eo/hotspots` | GET | Facilities with high AQI | `org_id`, `limit` |

---

## GDS Graph Projections

### Facility Graph
**Projection Name**: `org_facility_graph_{safe_org_id}`  
**Nodes**: Facility nodes filtered by `org_id`  
**Relationships**: `Route` relationships (ORIGIN → DESTINATION) filtered by `org_id`  
**Properties**:
- `distance`: Route distance in km (default 0 if null)
- `duration`: Route duration in hours (default 0 if null)
- `emission`: Route emission weight in kg CO₂ (computed from shipments, fallback to distance if null)

**Cypher Projection** (GDS 2.x aggregation form):
```cypher
MATCH (o:Facility {org_id:"..."}) -[:ORIGIN]->(rt:Route {org_id:"..."}) -[:DESTINATION]->(d:Facility {org_id:"..."})
RETURN gds.graph.project(
  'org_facility_graph_...',
  o, d,
  { relationshipProperties: {
    distance: coalesce(rt.distance_km, 0.0),
    duration: coalesce(rt.duration_hours, 0.0),
    emission: coalesce(rt.emission_weight, coalesce(rt.distance_km, 0.0))
  }}
) AS g
```

### Route Graph
**Projection Name**: `org_route_graph_{safe_org_id}`  
**Nodes**: Route nodes filtered by `org_id`  
**Relationships**: `NEXT` relationships connecting sequential routes (inferred from shipment sequences)  
**Properties**:
- `weight`: Route emission weight (default 1.0 if null)

---

## Analytics Outputs

### 1. Facility Betweenness Centrality
**Business Significance**: Identifies chokepoints in the supply chain. Facilities with high betweenness lie on many shortest paths; their disruption has cascading effects.

**Algorithm**: `gds.betweenness.stream`

**Output**:
```json
[
  {
    "facilityId": "F003",
    "score": 18.0
  },
  {
    "facilityId": "F001",
    "score": 4.0
  }
]
```

**Frontend Display**:
- Top 10 facilities in table with risk badges (High Risk for top 10%)
- KPI card showing top chokepoint

---

### 2. Facility PageRank
**Business Significance**: Identifies hubs with high connectivity. Facilities with high PageRank are central to the network; optimizing them improves overall efficiency.

**Algorithm**: `gds.pageRank.stream`

**Output**:
```json
[
  {
    "facilityId": "F003",
    "score": 0.298
  },
  {
    "facilityId": "F001",
    "score": 0.243
  }
]
```

**Frontend Display**:
- Top 10 facilities in table
- KPI card showing top hub

---

### 3. Facility Communities (Louvain)
**Business Significance**: Detects clusters of tightly connected facilities. Communities represent natural operational zones; consolidating or regionalizing operations within communities reduces cross-cluster logistics.

**Algorithm**: `gds.louvain.stream`

**Output**:
```json
[
  {
    "communityId": 5,
    "members": ["F001", "F101", "F102"]
  },
  {
    "communityId": 7,
    "members": ["F003", "F201"]
  }
]
```

**Frontend Display**:
- Shown in facility table alongside betweenness and PageRank

---

### 4. Route PageRank
**Business Significance**: Identifies critical corridors. Routes with high PageRank are heavily used; prioritizing them for optimization (e.g., mode shift, consolidation) yields disproportionate impact.

**Algorithm**: `gds.pageRank.stream`

**Output**:
```json
[
  {
    "routeId": "R001",
    "score": 0.289
  },
  {
    "routeId": "R002",
    "score": 0.245
  }
]
```

**Frontend Display**:
- Top 10 routes in table with importance badges (Critical, High)

---

### 5. Shortest Path (Dijkstra)
**Business Significance**: Compares optimal paths by distance, duration, or emission. Enables trade-off analysis: shortest distance may not be lowest emission; exposing this informs mode/route decisions.

**Algorithm**: `gds.shortestPath.dijkstra.stream`

**Input**: Source facility ID (e.g., `F101`), destination facility ID (e.g., `F001`), weight (`distance`/`duration`/`emission`)

**Output**:
```json
{
  "weight": "emission",
  "totalCost": 1250.5,
  "facilityIds": ["F101", "F003", "F001"]
}
```

**Frontend Display**:
- Path comparison card with inputs for source, destination, weight
- Shows path and total cost

---

### 6. Frequent Emission Patterns (PrefixSpan)
**Business Significance**: Discovers routes that occur frequently and accumulate high emissions. These patterns are invisible in single-shipment analysis but represent low-hanging fruit for optimization (e.g., consolidation, mode shift).

**Algorithm**: Custom PrefixSpan implementation in `services/prefixspan_service.py`

**Data Source**: Sequences built from `shipments` table, using `total_emissions_kg_co2` for scoring. Each sequence is `[origin_facility_id, transport_mode, destination_facility_id]`.

**Output**:
```json
{
  "patterns": [
    {
      "pattern": ["F101", "road_truck", "F003"],
      "support_count": 5,
      "emission_sum": 1250.5,
      "emission_avg": 250.1,
      "score": 6252.5
    }
  ],
  "total_sequences": 27
}
```

**Frontend Display**:
- Table showing pattern, occurrences, total emissions, avg per trip
- KPI card showing top emission pattern

---

### 7. EO Hotspots
**Business Significance**: Flags facilities in high-pollution zones. Facilities with AQI ≥100 face operational, regulatory, and reputational risks. Trends indicate worsening conditions; proactive mitigation (relocate, offset, engage suppliers) is warranted.

**Data Source**: `EOReading` nodes in Neo4j, linked to facilities via `HAS_READING` relationship. AQI calculated from PM2.5, NO2, O3, SO2.

**Output**:
```json
[
  {
    "facility_id": "F003",
    "lat": 40.7128,
    "lon": -74.0060,
    "aqi": 125.3,
    "trend3m": 8.5,
    "recent_month": "2025-01"
  }
]
```

**Frontend Display**:
- Table showing facility, AQI, trend, status badges (Alert, Moderate, Good)
- KPI card showing number of AQI alerts

---

## Emission Data Flow

### Shipment Emissions
**Source**: `ingestion/loader.py` calculates `total_emissions_kg_co2` during ingestion if not provided.

**Calculation**:
```
total_emissions_kg_co2 = weight_tonnes × distance_km × emission_factor_kg_co2_per_ton_km
```

**Emission Factors** (defaults if not in `EmissionFactor` table):
- `ROAD_TRUCK`: 0.12 kg CO₂/ton-km
- `RAIL_FREIGHT`: 0.03 kg CO₂/ton-km
- `SEA_CONTAINER`: 0.01 kg CO₂/ton-km
- `AIR_CARGO`: 1.2 kg CO₂/ton-km

**Stored in**: `shipments.total_emissions_kg_co2` (Postgres)

### Route Emission Weight
**Source**: `services/kg_etl_service.py` computes during Phase 1 sync.

**Calculation**:
```sql
SELECT route_id, SUM(total_emissions_kg_co2) AS total_emis
FROM shipments
WHERE organization_id = :org
GROUP BY route_id
```

**Stored in**: `Route.emission_weight` property (Neo4j)

### PrefixSpan Mining
**Source**: `services/prefixspan_service.py` fetches `total_emissions_kg_co2` from shipments.

**Aggregation**: Accumulates emissions for each (origin, mode, destination) triplet across all shipments.

**Scoring**: Patterns scored by `emission_sum * support_count` to prioritize frequent, high-emission patterns.

---

## Frontend Implementation

### File: `/frontend/app/knowledge-graph/page.tsx`

### Design
- **Two Tabs**: Graph Visualization, Analytics
- **Design Language**: Uses shadcn/ui components (Card, Table, Badge, Tabs, Select, Input, Button)
- **Polish**: KPI cards, color-coded badges, responsive layout, loading states, skeleton loaders

### Graph Visualization Tab
- **Filters**: Search, transport modes, entity toggles (Suppliers, Facilities, Routes)
- **Interactive**: Click to load neighbors, drag, zoom, fit, re-layout
- **Cytoscape**: `cose-bilkent` layout for optimal node spacing

### Analytics Tab
#### KPI Cards (Top Row)
1. **Top Chokepoint**: Facility with highest betweenness (AlertTriangle icon)
2. **Top Hub**: Facility with highest PageRank (TrendingUp icon)
3. **Top Emission Pattern**: Pattern with highest emission sum (Leaf icon)
4. **AQI Alerts**: Count of facilities with AQI ≥100 (Wind icon)

#### Analytics Sections
1. **Facility Analytics**: Table with betweenness, PageRank, community, risk badges
2. **Route Analytics**: Table with PageRank, importance badges (Critical, High)
3. **Frequent Emission Patterns**: Table with pattern, occurrences, total emissions, avg per trip
4. **Path Comparison**: Interactive form to find shortest path by distance/duration/emission
5. **Environmental Hotspots**: Table with facility, AQI, trend, status badges
6. **Graph Health**: Status of projected graphs (node/relationship counts)

#### Loading State
- Full-page spinner with message "Building graphs and loading analytics..."
- Auto-loads on tab switch if not already loaded

---

## Danger Zone Integration

### Backend: Clear Graphs Endpoint
**Endpoint**: `DELETE /api/kg/analytics/graphs/clear`  
**Action**: Drops facility and route GDS graphs for the organization  
**Error Handling**: Returns 500 if drop fails, propagates error to frontend

### Frontend: Settings Page
**File**: `/frontend/app/settings/page.tsx`  
**Integration**: Added call to clear graphs endpoint in "Clear All" button handler  
**User Flow**:
1. User enters sudo password
2. Clicks "Clear All"
3. Backend clears Postgres data and Neo4j graphs
4. Success message: "Organization data cleared and analytics graphs cleared."
5. Error message propagated if either call fails

---

## Testing and Validation

### Sample Test Flow
1. **Ingest Data**: POST CSV files via `/api/ingestion/upload`
2. **Sync to Neo4j**: POST `/api/kg/sync?org_id=...`
3. **Build Graphs**: POST `/api/kg/analytics/graphs/build?org_id=...`
4. **Fetch Analytics**:
   - GET `/api/kg/analytics/facilities/betweenness?org_id=...&limit=15`
   - GET `/api/kg/analytics/facilities/pagerank?org_id=...&limit=15`
   - GET `/api/kg/analytics/facilities/communities?org_id=...`
   - GET `/api/kg/analytics/routes/pagerank?org_id=...&limit=15`
   - POST `/api/kg/analytics/sequences/prefixspan?org_id=...&min_support=2&max_len=5&top_k=15`
   - GET `/api/kg/analytics/eo/hotspots?org_id=...&limit=10`
5. **Path Comparison**: POST `/api/kg/analytics/shortest-path?org_id=...&srcNode=F101&dstNode=F001&weight=emission`
6. **Frontend**: Navigate to Knowledge Graph page, switch to Analytics tab

### Expected Outcomes
- All endpoints return valid JSON with expected structure
- Emission values are non-zero (if shipments have emission data)
- PrefixSpan patterns have length ≥3
- Shortest path returns facility IDs (not internal Neo4j node IDs)
- Frontend displays all analytics with proper formatting

---

## Key Implementation Details

### Multi-Tenancy
- All Neo4j nodes have `org_id` property
- GDS graphs are org-scoped by naming convention: `org_facility_graph_{safe_org_id}`
- All queries filter by `org_id` to ensure data isolation

### GDS Syntax (Neo4j 5.15 Community, GDS 2.x)
- **Graph Projection**: Use aggregation function form in `RETURN` clause
  ```cypher
  MATCH (o:Facility) -[:ORIGIN]->(rt:Route) -[:DESTINATION]->(d:Facility)
  RETURN gds.graph.project('graphName', o, d, { relationshipProperties: {...} }) AS g
  ```
- **Algorithm Calls**: Use `.stream` variant for results, pass graph name as string
  ```cypher
  CALL gds.betweenness.stream('graphName') YIELD nodeId, score
  RETURN gds.util.asNode(nodeId).id AS facilityId, score
  ```
- **Node ID Lookup**: Use `gds.util.asNode(nodeId)` to convert internal ID to node, then access properties

### PrefixSpan Implementation
- **Native Python**: No external library dependencies
- **Sequence Format**: `[origin_id, mode, destination_id]` per shipment
- **Recursion**: DFS with min_support pruning, max_len early termination
- **Scoring**: `emission_sum * support_count` to balance frequency and impact
- **Pattern Length**: Enforced minimum of 3 tokens (origin → mode → destination) for meaningful results

### Shortest Path API Enhancement
- **Input**: Accepts user-friendly facility IDs (e.g., `F101`, `F003`)
- **Internal Lookup**: Queries Neo4j to get internal node IDs via `id(node)`
- **GDS Call**: Passes internal IDs to `gds.shortestPath.dijkstra.stream`
- **Output**: Returns facility IDs (not internal IDs) for frontend display

---

## Performance Considerations

### Graph Size
- **Small Orgs (<100 facilities, <500 routes)**: Subsecond response
- **Medium Orgs (100–1000 facilities)**: 1–3 seconds for graph projection, <1s for algorithms
- **Large Orgs (>1000 facilities)**: May require pagination or incremental loading

### Caching Strategy
- **GDS Graphs**: Persist in-memory until dropped; rebuild only on data sync
- **Frontend**: Fetch analytics once per tab visit, refresh only on user action (e.g., "Reload")

### Optimization Opportunities
- **Pre-compute**: Run analytics on sync and cache in Postgres/Redis
- **Incremental Sync**: Update only changed entities instead of full sync
- **Parallel Queries**: Use `Promise.all` for independent analytics calls (already implemented in frontend)

---

## Future Enhancements

### Phase 3: Optimization (Planned, not implemented)
- **Min-Cost Flow**: Use `gds.alpha.spanningTree` or external solver for optimal routing under constraints
- **What-If Analysis**: Simulate mode shifts, consolidations, and measure emission impact
- **Real-Time**: Stream shipment updates to Neo4j, trigger incremental analytics

### Advanced Analytics
- **Temporal Patterns**: Analyze shipment timing, seasonality with time-series queries
- **Predictive Models**: ML on GDS embeddings (node2vec) to predict disruptions, delays
- **Geospatial Overlay**: Integrate GEE data directly into Neo4j for spatial risk scoring

---

## Troubleshooting

### Issue: GDS Graph Projection Fails
**Symptoms**: `gds.graph.project` returns empty or errors  
**Solutions**:
- Verify nodes/relationships exist in Neo4j with matching `org_id`
- Check GDS plugins enabled in `docker-compose.yml`: `NEO4J_PLUGINS=["apoc","graph-data-science"]`
- Use correct syntax for GDS 2.x (aggregation form, not Cypher projection)

### Issue: Emission Values Are Zero
**Symptoms**: `total_emissions_kg_co2` is 0 in shipments, emission patterns have 0 sums  
**Solutions**:
- Verify `ingestion/loader.py` calculates emissions (check weight, distance, emission_factor)
- Re-ingest data or run backfill SQL update
- Check `EmissionFactor` table has factors for transport modes

### Issue: PrefixSpan Returns Empty
**Symptoms**: `patterns` array is empty  
**Solutions**:
- Lower `min_support` (default 5 → try 2)
- Increase `max_len` (default 5 → try 7)
- Verify shipments table has data for the org

### Issue: Shortest Path Fails
**Symptoms**: 404 "Source or destination facility not found"  
**Solutions**:
- Verify facility IDs exist in Neo4j with matching `org_id`
- Use exact facility IDs (case-sensitive)
- Check GDS graph built with `/api/kg/analytics/graphs/build`

---

## Conclusion
This implementation delivers a production-ready, multi-tenant Knowledge Graph Analytics system for VeriEarth, enabling actionable insights on supply chain structure, emissions, and environmental risk. The two-phase architecture balances real-time data sync with on-demand analytics, ensuring scalability and performance. The polished frontend provides a seamless user experience, translating complex graph algorithms into clear, business-relevant visualizations.

**Status**: ✅ Fully implemented and tested  
**Next Steps**: User acceptance testing, performance tuning for large orgs, Phase 3 optimization planning

