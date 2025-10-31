# Redis Caching Strategy for VeriEarth

## Overview
Redis is already configured in `docker-compose.yml` but not yet implemented. This document identifies all effective caching opportunities across the codebase.

---

## 1. **Google Earth Engine (GEE) API Calls** 🔥 HIGHEST PRIORITY

### Current State
- **File**: `aqi/gee_service.py`
- **Operations**: Fetching pollutant data (NO2, CO, SO2, O3, HCHO, CH4, AOD)
- **Cost**: Expensive external API calls (quota limits, slow responses ~5-30s per request)
- **Frequency**: Called on-demand for reports, facility enrichment

### Caching Strategy
**Cache Key Format**: `gee:aoi:{aoi_hash}:{start_date}:{end_date}:{interval}`

**TTL**: 
- Daily data: 24 hours
- Weekly data: 7 days  
- Monthly data: 30 days
- Yearly data: 365 days

**Implementation Points**:
1. `aqi/gee_service.py::fetch_pollutant_data()` - Cache entire response
2. `routes/report_routes.py::fetch_and_generate_report()` - Cache before background task
3. `services/background_eo_service.py::_enrich_single_facility()` - Cache monthly snapshots per facility

**Estimated Impact**: 
- Reduce GEE API calls by 70-90%
- Response time: 30s → <1s (cache hit)
- Cost savings on GEE quota

---

## 2. **Neo4j GDS Graph Analytics** 🔥 HIGH PRIORITY

### Current State
- **Files**: `routes/kg_analytics_routes.py`
- **Operations**: 
  - Graph projections (`gds.graph.project`)
  - Betweenness Centrality
  - PageRank
  - Louvain Communities
  - Shortest Path (Dijkstra)
- **Cost**: Expensive graph computations (1-5s for medium orgs, up to 30s for large)
- **Frequency**: Called every time user opens Analytics tab

### Caching Strategy
**Cache Key Format**: `gds:{org_id}:{algorithm}:{params_hash}`

**TTL**: 
- Graph projections: Until data sync (invalidate on `/api/kg/sync`)
- Algorithm results: 15 minutes (refreshable on-demand)

**Implementation Points**:
1. `routes/kg_analytics_routes.py`:
   - `facilities_betweenness()` - Cache top N results
   - `facilities_pagerank()` - Cache top N results
   - `facilities_communities()` - Cache full community list
   - `routes_pagerank()` - Cache route rankings
   - `routes_betweenness()` - Cache route betweenness
   - `routes_communities()` - Cache route communities
   - `shortest_path()` - Cache by `{org_id}:{src}:{dst}:{weight}`

2. `services/kg_etl_service.py`:
   - `sync_phase1()` - Invalidate all analytics caches on sync
   - `ensure_graphs_for_org()` - Cache graph status (node/edge counts)

**Cache Invalidation**:
- Clear on: POST `/api/kg/sync`, DELETE `/api/kg/analytics/graphs/clear`
- Pattern: `gds:{org_id}:*`

**Estimated Impact**:
- Response time: 3-5s → <100ms (cache hit)
- Neo4j load: Reduced by 60-80%
- Better UX: Instant analytics refresh

---

## 3. **PrefixSpan Pattern Mining** 🔥 HIGH PRIORITY

### Current State
- **File**: `routes/kg_analytics_routes.py::mine_prefixspan()`
- **Operations**: Sequential pattern mining on shipments
- **Cost**: CPU-intensive, scans all shipments (5000 limit currently)
- **Frequency**: Called on Analytics tab load

### Caching Strategy
**Cache Key Format**: `prefixspan:{org_id}:{min_support}:{max_len}:{top_k}`

**TTL**: 30 minutes (patterns don't change frequently)

**Implementation Points**:
- `routes/kg_analytics_routes.py::mine_prefixspan()` - Cache entire response

**Cache Invalidation**:
- Clear on: New shipment ingestion, POST `/api/kg/sync`
- Pattern: `prefixspan:{org_id}:*`

**Estimated Impact**:
- Response time: 2-5s → <100ms (cache hit)
- CPU usage: Reduced by 80%+

---

## 4. **Dashboard KPIs and Aggregations** 🟡 MEDIUM PRIORITY

### Current State
- **File**: `routes/dashboard_routes.py`
- **Operations**: Complex SQL aggregations with JOINs
  - `get_kpis()` - Multiple subqueries, date range calculations
  - `emissions_trend()` - Time-series aggregation
  - `transport_distribution()` - Group by transport mode
  - `top_routes()` - Top N with facility name lookups
  - `carriers()` - Carrier statistics
  - `facilities_aqi()` - Latest EO readings per facility
- **Cost**: Heavy PostgreSQL queries (500ms-2s)
- **Frequency**: Called on every dashboard load

### Caching Strategy
**Cache Key Format**: `dashboard:{org_id}:{endpoint}:{params_hash}`

**TTL**: 
- KPIs: 5 minutes (frequently changing)
- Trends: 15 minutes (time-series data)
- Top routes/carriers: 10 minutes

**Implementation Points**:
- `routes/dashboard_routes.py`:
  - `get_kpis()` - Cache by `{org_id}:{date_from}:{date_to}:{facility_id}:{supplier_id}`
  - `emissions_trend()` - Cache by `{org_id}:{date_from}:{date_to}:{interval}`
  - `transport_distribution()` - Cache by `{org_id}:{date_from}:{date_to}`
  - `top_routes()` - Cache by `{org_id}:{date_from}:{date_to}:{limit}`
  - `carriers()` - Cache by `{org_id}:{date_from}:{date_to}:{limit}`
  - `facilities_aqi()` - Cache by `{org_id}:{limit}`

**Cache Invalidation**:
- Clear on: New shipment, route, facility data ingestion
- Pattern: `dashboard:{org_id}:*`

**Estimated Impact**:
- Response time: 1-2s → <50ms (cache hit)
- Database load: Reduced by 50-70%

---

## 5. **Knowledge Graph Queries** 🟡 MEDIUM PRIORITY

### Current State
- **File**: `routes/kg_routes.py::get_graph()`
- **Operations**: Neo4j Cypher queries for graph visualization
- **Cost**: Moderate (100-500ms)
- **Frequency**: Called on every filter change in Graph tab

### Caching Strategy
**Cache Key Format**: `kg:graph:{org_id}:{filters_hash}`

**TTL**: 5 minutes (filters can change frequently)

**Implementation Points**:
- `routes/kg_routes.py::get_graph()` - Cache filtered graph results
- Hash filter params: `{modes}:{min_km}:{max_km}:{include_suppliers}:{include_facilities}:{include_routes}:{q}`

**Cache Invalidation**:
- Clear on: POST `/api/kg/sync`
- Pattern: `kg:graph:{org_id}:*`

**Estimated Impact**:
- Response time: 200-500ms → <50ms (cache hit)
- Neo4j load: Reduced by 40-60%

---

## 6. **Data Management Entity Lists** 🟢 LOW PRIORITY

### Current State
- **File**: `routes/data_management_routes.py`
- **Operations**: 
  - `get_stats()` - Count queries for all entities
  - `get_entity_data()` - Full entity lists (facilities, shipments, routes, etc.)
- **Cost**: Moderate PostgreSQL queries (200-800ms)
- **Frequency**: Called on Data Management page load

### Caching Strategy
**Cache Key Format**: `dm:{org_id}:{entity_type}`

**TTL**: 
- Stats: 2 minutes
- Entity lists: 5 minutes

**Implementation Points**:
- `routes/data_management_routes.py`:
  - `get_stats()` - Cache counts
  - `get_entity_data()` - Cache full lists per entity type

**Cache Invalidation**:
- Clear on: Entity create/update/delete
- Pattern: `dm:{org_id}:{entity_type}`, `dm:{org_id}:stats`

**Estimated Impact**:
- Response time: 300-800ms → <50ms (cache hit)
- Database load: Reduced by 40-50%

---

## 7. **EO Hotspots** 🟡 MEDIUM PRIORITY

### Current State
- **File**: `routes/kg_analytics_routes.py::eo_hotspots()`
- **Operations**: Neo4j query for latest AQI per facility with trends
- **Cost**: Moderate Neo4j query (200-500ms)
- **Frequency**: Called on Analytics tab load

### Caching Strategy
**Cache Key Format**: `eo:hotspots:{org_id}:{limit}`

**TTL**: 15 minutes (EO data updated monthly)

**Implementation Points**:
- `routes/kg_analytics_routes.py::eo_hotspots()` - Cache sorted list

**Cache Invalidation**:
- Clear on: New EO reading ingestion, POST `/api/kg/sync`
- Pattern: `eo:hotspots:{org_id}:*`

**Estimated Impact**:
- Response time: 200-500ms → <50ms (cache hit)

---

## 8. **Organization Status and Sync Status** 🟢 LOW PRIORITY

### Current State
- **Files**: 
  - `routes/kg_routes.py::get_kg_sync_status()`
  - `routes/organization_routes.py` (if exists)
- **Operations**: Count queries across Postgres and Neo4j
- **Cost**: Multiple queries, moderate (300-600ms)
- **Frequency**: Called occasionally to check sync state

### Caching Strategy
**Cache Key Format**: `kg:status:{org_id}`

**TTL**: 30 seconds (status can change during sync)

**Implementation Points**:
- `routes/kg_routes.py::get_kg_sync_status()` - Cache status object

**Cache Invalidation**:
- Clear on: POST `/api/kg/sync`, data ingestion
- Pattern: `kg:status:{org_id}`

---

## Implementation Plan

### Phase 1: High-Impact Quick Wins (Week 1)
1. ✅ Redis client setup and dependency injection
2. ✅ GEE API response caching
3. ✅ GDS analytics caching (betweenness, pagerank, communities)
4. ✅ PrefixSpan pattern caching

### Phase 2: Dashboard and Graph Caching (Week 2)
5. ✅ Dashboard KPI caching
6. ✅ Knowledge graph query caching
7. ✅ EO hotspots caching

### Phase 3: Entity List Caching (Week 3)
8. ✅ Data management entity caching
9. ✅ Organization status caching

### Phase 4: Advanced Features
10. ✅ Cache warming on data sync
11. ✅ Cache hit/miss metrics
12. ✅ Automatic cache invalidation hooks

---

## Cache Key Naming Convention

**Format**: `{namespace}:{org_id}:{operation}:{params}`

**Examples**:
- `gee:aoi:abc123:2024-01-01:2024-01-31:month`
- `gds:ecfc141e-2e55-4670-bb8e-9e8813b02866:betweenness:facilities:15`
- `dashboard:ecfc141e-2e55-4670-bb8e-9e8813b02866:kpis:2024-01-01:2024-01-31`
- `prefixspan:ecfc141e-2e55-4670-bb8e-9e8813b02866:2:5:15`

**Benefits**:
- Easy pattern matching for invalidation
- Clear namespace separation
- Org-scoped for multi-tenancy

---

## Cache Invalidation Strategy

### Automatic Invalidation Triggers

1. **Data Ingestion** → Clear relevant caches
   - New shipment → `dashboard:{org_id}:*`, `prefixspan:{org_id}:*`
   - New facility → `kg:graph:{org_id}:*`, `dm:{org_id}:*`
   - New route → `kg:graph:{org_id}:*`, `gds:{org_id}:*`

2. **KG Sync** → Clear all org caches
   - POST `/api/kg/sync` → `gds:{org_id}:*`, `kg:*`, `prefixspan:{org_id}:*`

3. **Entity Updates** → Clear entity-specific caches
   - Update facility → `dm:{org_id}:facilities`, `kg:graph:{org_id}:*`

4. **Time-based Expiration** → TTL-based (no manual invalidation needed)

---

## Redis Connection Setup

### Required Changes

1. **Add Redis client to `config.py`**:
```python
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
```

2. **Create Redis service module** (`db/redis_service.py`):
```python
import redis
from config import REDIS_URL
import json
from typing import Optional, Any

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def cache_get(key: str) -> Optional[Any]:
    """Get cached value"""
    val = redis_client.get(key)
    return json.loads(val) if val else None

def cache_set(key: str, value: Any, ttl: int = 3600):
    """Set cached value with TTL"""
    redis_client.setex(key, ttl, json.dumps(value))

def cache_delete(pattern: str):
    """Delete keys matching pattern"""
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
```

3. **Add dependency in routes**:
```python
from db.redis_service import cache_get, cache_set, cache_delete
```

---

## Performance Expectations

### Before Caching
- GEE calls: 30s average
- GDS analytics: 3-5s average
- Dashboard KPIs: 1-2s average
- Graph queries: 200-500ms average

### After Caching (Cache Hit)
- GEE calls: <50ms (600x faster)
- GDS analytics: <100ms (30-50x faster)
- Dashboard KPIs: <50ms (20-40x faster)
- Graph queries: <50ms (4-10x faster)

### Expected Cache Hit Rates
- GEE: 70-90% (same AOI/date ranges requested multiple times)
- GDS: 60-80% (users refresh analytics frequently)
- Dashboard: 50-70% (dashboard reloads)
- Graph: 30-50% (filters change frequently)

---

## Monitoring and Metrics

### Key Metrics to Track
1. **Cache hit rate** per namespace
2. **Cache memory usage** (Redis `INFO memory`)
3. **Average response time** (with vs without cache)
4. **Cache invalidation frequency**

### Redis Commands for Monitoring
```bash
# Cache hit rate (custom metric)
redis-cli --stat

# Memory usage
redis-cli INFO memory

# Key counts by pattern
redis-cli --scan --pattern "gds:*" | wc -l
```

---

## Summary: Priority Order

### 🔥 **Critical (Implement First)**
1. GEE API caching - Highest cost, slowest operations
2. GDS analytics caching - Expensive graph computations
3. PrefixSpan caching - CPU-intensive pattern mining

### 🟡 **High Value**
4. Dashboard KPIs - Frequently accessed, complex queries
5. EO hotspots - Moderate cost, frequent access
6. Graph visualization queries - User interaction heavy

### 🟢 **Nice to Have**
7. Entity lists - Moderate benefit
8. Organization status - Low frequency

---

## Estimated Total Impact

- **API Response Time**: 60-80% reduction overall
- **Database Load**: 50-70% reduction
- **External API Calls**: 70-90% reduction (GEE)
- **User Experience**: Near-instant page loads on cache hits
- **Cost Savings**: Reduced GEE quota usage, lower infrastructure costs

**Implementation Effort**: ~2-3 weeks for full implementation
**ROI**: High - Immediate performance improvements, scalable architecture

