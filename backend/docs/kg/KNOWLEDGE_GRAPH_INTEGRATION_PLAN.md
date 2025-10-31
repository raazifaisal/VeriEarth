# Knowledge Graph Integration Plan

## PostgreSQL Data Models (Complete Schema)

### Core Multi-Tenancy
- **Organization**: id, name, schema_name, industry, subscription_tier, is_active
- **User**: id, email, hashed_password, full_name, oauth_provider, oauth_id, is_active, is_verified
- **UserOrganization**: id, user_id, organization_id, role (junction table)

### Supply Chain Entities
- **Supplier**: id, organization_id, name, address, city, region, country, postal_code, latitude, longitude, tier_level, certifications, contact_email, contact_phone, is_active
- **Product**: id, organization_id, name, category, uom, weight_kg, volume_m3, carbon_intensity_per_unit, is_active
- **Facility**: id, organization_id, supplier_id (nullable - supplier ownership), name, facility_type (enum: manufacturing, warehouse, distribution_center, port, retail), location (PostGIS POINT), address, city, country, capacity_tons, is_active
- **Route**: id, organization_id, origin_facility_id, destination_facility_id, transport_mode (enum: road_truck, road_van, rail_freight, air_cargo, sea_container, sea_bulk, pipeline), distance_km, duration_hours, is_multi_leg, intermediate_stops (JSON), is_active
- **PurchaseOrder**: id, organization_id, po_id, po_line_id, supplier_id, facility_id, product_id, quantity, unit_price, total_cost, order_date, expected_delivery_date, transport_mode, currency, status
- **Shipment**: id, organization_id, route_id, weight_kg, volume_m3, cost_per_kg, total_cost, emission_factor_kg_co2_per_ton_km, emissions_per_kg, total_emissions_kg_co2, shipment_date, planned_delivery_date, actual_delivery_date, status (enum: planned, in_transit, delivered, delayed, cancelled), carrier, tracking_number, extra_metadata (JSON)
- **EmissionFactor**: id, transport_mode, vehicle_type, emission_factor_kg_co2_per_ton_km, source, region, effective_date

### Environmental Data
- **FacilityEnvironmentalData**: id, facility_id, organization_id, captured_at, no2_value, co_value, hcho_value, ch4_value, so2_value, aod_value, o3_value, aqi_score, pollution_level
- **FacilityEOTimeseries** (referenced in routes): id, facility_id, organization_id, observed_at, aqi_score, no2, co, so2, o3, ch4, aod (monthly rollups)

## Neo4j Knowledge Graph Structure

### Node Types (Labels)
1. **Organization**: {id, name, industry, subscription_tier}
2. **Supplier**: {id, org_id, name, tier_level, city, country, region, certifications, contact_email, contact_phone, is_active, created_at, updated_at}
3. **Facility**: {id, org_id, name, facility_type, city, country, address, capacity_tons, latitude, longitude, is_active, location (point), created_at, updated_at}
4. **Product**: {id, org_id, name, category, uom, weight_kg, carbon_intensity_per_unit, is_active, created_at, updated_at}
5. **PurchaseOrder**: {id, org_id, po_id, po_line_id, quantity, unit_price, total_cost, order_date, expected_delivery_date, transport_mode, currency, status, created_at, updated_at}
6. **Route**: {id, org_id, transport_mode, distance_km, duration_hours, is_multi_leg, intermediate_stops, is_active, created_at, updated_at}
7. **Shipment**: {id, org_id, weight_kg, volume_m3, total_cost, total_emissions_kg_co2, shipment_date, planned_delivery_date, actual_delivery_date, status, carrier, tracking_number, created_at, updated_at}
8. **EOReading**: {id, facility_id, org_id, observed_at, aqi_score, no2, co, so2, o3, ch4, aod, pollution_level, created_at} (monthly snapshots aggregated from facility_eo_timeseries)

### Relationships (Types)
- **(Organization)-[:HAS_SUPPLIER]->(Supplier)**
- **(Organization)-[:HAS_FACILITY]->(Facility)**
- **(Supplier)-[:OWNS]->(Facility)** (when facility.supplier_id is not null)
- **(PurchaseOrder)-[:FOR_PRODUCT]->(Product)**
- **(Supplier)-[:RECEIVES_PO]->(PurchaseOrder)**
- **(PurchaseOrder)-[:FULFILLED_AT]->(Facility)**
- **(Route)-[:ORIGIN]->(Facility)**
- **(Route)-[:DESTINATION]->(Facility)**
- **(Shipment)-[:USES_ROUTE]->(Route)**
- **(Shipment)-[:BELONGS_TO]->(Organization)**
- **(Facility)-[:HAS_EO_READING]->(EOReading)** (monthly snapshots, one per facility per month)
- **(Organization)-[:HAS_PRODUCT]->(Product)**

## ETL Integration Strategy

### Phase 1: Core Supply Chain Graph (MVP)
**Nodes**: Organization, Supplier, Facility, Route, Shipment, EOReading (monthly snapshots). **Relationships**: Organization→Supplier/Facility, Supplier→OWNS→Facility, Route→ORIGIN/DESTINATION, Shipment→USES_ROUTE, Facility→HAS_EO_READING (monthly). **Use cases**: Top emission-heavy transport legs, supplier-owned facilities with poor AQI, route frequency analysis, monthly pollution trends.

### Phase 2: Procurement Integration
**Nodes**: Product, PurchaseOrder. **Relationships**: PurchaseOrder→FOR_PRODUCT, Supplier→RECEIVES_PO, PurchaseOrder→FULFILLED_AT→Facility, Organization→HAS_PRODUCT. **Use cases**: Procurement-to-shipment traceability, product flow through supply chain, supplier performance by PO volume.

### Phase 3: Derived Analytics & Graph Data Science
**Nodes**: Derived Facility relationships. **Relationships**: Supplier→FEEDS→Facility (via dominant routes/POs), Facility→CONNECTED_TO (high-frequency routes). **Use cases**: Supplier facility impact on organization DCs, sequence mining patterns, route centrality analysis, GDS community detection for supply clusters.

### Neo4j Constraints & Indexes

**Unique Constraints** (run once per entity type):
```cypher
CREATE CONSTRAINT org_unique IF NOT EXISTS FOR (o:Organization) REQUIRE (o.id) IS UNIQUE;
CREATE CONSTRAINT supplier_unique IF NOT EXISTS FOR (s:Supplier) REQUIRE (s.id) IS UNIQUE;
CREATE CONSTRAINT facility_unique IF NOT EXISTS FOR (f:Facility) REQUIRE (f.id) IS UNIQUE;
CREATE CONSTRAINT route_unique IF NOT EXISTS FOR (r:Route) REQUIRE (r.id) IS UNIQUE;
CREATE CONSTRAINT product_unique IF NOT EXISTS FOR (p:Product) REQUIRE (p.id) IS UNIQUE;
CREATE CONSTRAINT po_unique IF NOT EXISTS FOR (po:PurchaseOrder) REQUIRE (po.id) IS UNIQUE;
CREATE CONSTRAINT shipment_unique IF NOT EXISTS FOR (sh:Shipment) REQUIRE (sh.id) IS UNIQUE;
CREATE CONSTRAINT eoread_unique IF NOT EXISTS FOR (e:EOReading) REQUIRE (e.id) IS UNIQUE;
```

**Performance Indexes**:
```cypher
CREATE INDEX facility_city IF NOT EXISTS FOR (f:Facility) ON (f.city);
CREATE INDEX facility_org IF NOT EXISTS FOR (f:Facility) ON (f.org_id);
CREATE INDEX route_mode IF NOT EXISTS FOR (r:Route) ON (r.transport_mode);
CREATE INDEX shipment_date IF NOT EXISTS FOR (sh:Shipment) ON (sh.shipment_date);
CREATE INDEX supplier_tier IF NOT EXISTS FOR (s:Supplier) ON (s.tier_level);
CREATE INDEX eo_observed_at IF NOT EXISTS FOR (e:EOReading) ON (e.observed_at);
```

**Spatial Index** (for nearest-neighbor queries):
```cypher
// After setting location points: SET f.location = point({longitude: $lon, latitude: $lat})
CREATE POINT INDEX facility_location IF NOT EXISTS FOR (f:Facility) ON (f.location);
```

### ETL Implementation Approach

**Idempotent Upserts**: Use Cypher MERGE on `{id: $id}` for all nodes. Pattern: `MERGE (n:Label {id: $id}) ON CREATE SET ... ON MATCH SET ...`. All relationships use `MERGE` after nodes exist.

**Batch Processing**: Process 500-1000 rows per transaction using `UNWIND` for bulk operations. Dependency order: Organization → Supplier → Facility → Route → Shipment → EOReading (Phase 1). Add Product → PurchaseOrder in Phase 2.

**Incremental Sync**: Track `last_synced_at` per organization in control table. Query PostgreSQL with `WHERE updated_at > last_synced_at` for delta sync. EOReading: aggregate `facility_eo_timeseries` to monthly snapshots (one node per facility per month from PostgreSQL monthly rolls).

**Multi-Tenancy**: All nodes include `org_id` property. Filter all queries with `WHERE node.org_id = $org_id`. Use separate databases or Enterprise scoped roles if strict isolation needed.

**EOReading Monthly Aggregation**: From `facility_eo_timeseries`, group by `facility_id, DATE_TRUNC('month', observed_at)` → compute avg/max AQI and pollutant values → create one EOReading node per facility-month with `id = facility_id + '::' + year_month`.

**Data Quality**: Validate foreign keys before creating relationships. Handle orphans: skip relationship if referenced node missing (log to data-quality queue) OR create placeholder node with `is_placeholder=true`.

**Derived Relationships (Phase 3)**: Compute `(:Supplier)-[:FEEDS]->(:Facility)` by aggregating POs/shipments where supplier→facility volume exceeds threshold. Use GDS for route centrality, community detection on supplier-facility networks.

### Performance & Monitoring
- Monitor transaction memory during bulk imports (use `PROFILE` on queries).
- Keep property cardinality reasonable (avoid large JSON blobs for filterable properties).
- Add `created_at`/`updated_at` timestamps to all nodes for ETL audit trail.
