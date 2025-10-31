# PostgreSQL Database Schema for Knowledge Graph

## Overview
This document provides a complete snapshot of all PostgreSQL tables for building the Neo4j Knowledge Graph. All data is stored in PostgreSQL/PostGIS, and the Knowledge Graph will be built FROM this data.

---

## 1. ORGANIZATIONS
**Purpose**: Multi-tenant organization management

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| name | VARCHAR | NOT NULL | Organization name |
| schema_name | VARCHAR | NOT NULL | Unique schema identifier |
| industry | VARCHAR | NULL | Industry type |
| is_active | BOOLEAN | NULL | Active status |
| subscription_tier | VARCHAR | NULL | Subscription level |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- Parent to: facilities, suppliers, products, purchase_orders, routes, shipments, facility_environmental_data

---

## 2. FACILITIES
**Purpose**: Physical locations (warehouses, manufacturing, distribution centers)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| organization_id | VARCHAR | NOT NULL | FK → organizations |
| name | VARCHAR | NOT NULL | Facility name |
| facility_type | ENUM(facilitytype) | NOT NULL | warehouse/manufacturing/distribution_center/retail |
| location | GEOMETRY(Point,4326) | NULL | PostGIS point (lat/lon) |
| address | TEXT | NULL | Full address |
| city | VARCHAR | NULL | City |
| country | VARCHAR | NULL | Country |
| capacity_tons | DOUBLE PRECISION | NULL | Storage/production capacity |
| is_active | BOOLEAN | NULL | Active status |
| neo4j_node_id | VARCHAR | NULL | Legacy field (not used) |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- Parent to: routes (origin & destination), purchase_orders, facility_environmental_data

**Indexes**:
- PRIMARY KEY: id
- GIST INDEX: location (spatial queries)

---

## 3. SUPPLIERS
**Purpose**: Supplier information for procurement

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| name | VARCHAR | NOT NULL | Supplier name |
| organization_id | VARCHAR | NULL | FK → organizations |
| location | GEOMETRY(Point,4326) | NULL | PostGIS point (lat/lon) |
| address | VARCHAR | NULL | Address |
| city | VARCHAR | NULL | City |
| region | VARCHAR | NULL | Region/state |
| country | VARCHAR | NULL | Country |
| postal_code | VARCHAR | NULL | Postal code |
| latitude | DOUBLE PRECISION | NULL | Latitude (backup) |
| longitude | DOUBLE PRECISION | NULL | Longitude (backup) |
| tier_level | VARCHAR | NULL | tier_1, tier_2, etc. |
| certifications | VARCHAR | NULL | ISO9001, ISO14001, etc. |
| sustainability_score | DOUBLE PRECISION | NULL | ESG score |
| contact_email | VARCHAR | NULL | Contact email |
| contact_phone | VARCHAR | NULL | Contact phone |
| is_active | BOOLEAN | NULL | Active status |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- Parent to: purchase_orders

**Indexes**:
- PRIMARY KEY: id
- GIST INDEX: location (spatial queries)

---

## 4. PRODUCTS
**Purpose**: Product catalog with ESG data

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| name | VARCHAR | NOT NULL | Product name |
| organization_id | VARCHAR | NOT NULL | FK → organizations |
| category | VARCHAR | NULL | Product category |
| uom | VARCHAR | NULL | Unit of measure (KG, EA, L, etc.) |
| weight_kg | DOUBLE PRECISION | NULL | Weight in kg |
| volume_m3 | DOUBLE PRECISION | NULL | Volume in cubic meters |
| carbon_intensity_per_unit | DOUBLE PRECISION | NULL | kg CO2 per unit |
| is_active | BOOLEAN | NULL | Active status |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- Parent to: purchase_orders

---

## 5. PURCHASE_ORDERS
**Purpose**: Purchase orders linking suppliers, facilities, and products

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key (composite: po_id-po_line_id) |
| po_id | VARCHAR | NOT NULL | Purchase order number |
| po_line_id | VARCHAR | NOT NULL | Line item number |
| organization_id | VARCHAR | NOT NULL | FK → organizations |
| supplier_id | VARCHAR | NULL | FK → suppliers |
| facility_id | VARCHAR | NULL | FK → facilities (destination) |
| product_id | VARCHAR | NULL | FK → products |
| quantity | DOUBLE PRECISION | NOT NULL | Order quantity |
| unit_price | DOUBLE PRECISION | NOT NULL | Price per unit |
| total_cost | DOUBLE PRECISION | NOT NULL | Total line cost |
| order_date | TIMESTAMP WITH TZ | NULL | Order date |
| expected_delivery_date | TIMESTAMP WITH TZ | NULL | Expected delivery |
| transport_mode | VARCHAR | NULL | Transport method |
| currency | VARCHAR | NULL | Currency (USD, EUR, etc.) |
| status | VARCHAR | NULL | Order status |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- FK: supplier_id → suppliers
- FK: facility_id → facilities
- FK: product_id → products

**KG Insight**: Central node connecting Supplier → Product → Facility supply chain

---

## 6. ROUTES
**Purpose**: Transportation routes between facilities

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| organization_id | VARCHAR | NOT NULL | FK → organizations |
| origin_facility_id | VARCHAR | NOT NULL | FK → facilities (origin) |
| destination_facility_id | VARCHAR | NOT NULL | FK → facilities (destination) |
| transport_mode | ENUM(transportmode) | NOT NULL | road_truck/rail_freight/sea_container/air_freight |
| distance_km | DOUBLE PRECISION | NOT NULL | Distance in kilometers |
| duration_hours | DOUBLE PRECISION | NULL | Transit duration |
| is_multi_leg | BOOLEAN | NULL | Multiple stops |
| intermediate_stops | JSON | NULL | Array of intermediate facilities |
| is_active | BOOLEAN | NULL | Active status |
| neo4j_relationship_id | VARCHAR | NULL | Legacy field (not used) |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- FK: origin_facility_id → facilities
- FK: destination_facility_id → facilities
- Parent to: shipments

**KG Insight**: Direct relationship/edge between facilities in the graph

---

## 7. SHIPMENTS
**Purpose**: Actual shipment data with ESG metrics

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| organization_id | VARCHAR | NOT NULL | FK → organizations |
| route_id | VARCHAR | NOT NULL | FK → routes |
| weight_kg | DOUBLE PRECISION | NOT NULL | Shipment weight |
| volume_m3 | DOUBLE PRECISION | NULL | Shipment volume |
| cost_per_kg | DOUBLE PRECISION | NULL | Cost per kg |
| total_cost | DOUBLE PRECISION | NOT NULL | Total shipment cost |
| emission_factor_kg_co2_per_ton_km | DOUBLE PRECISION | NULL | Emission factor |
| emissions_per_kg | DOUBLE PRECISION | NULL | Emissions per kg |
| total_emissions_kg_co2 | DOUBLE PRECISION | NOT NULL | Total emissions |
| shipment_date | TIMESTAMP | NOT NULL | Pickup date |
| planned_delivery_date | TIMESTAMP | NULL | Planned delivery |
| actual_delivery_date | TIMESTAMP | NULL | Actual delivery |
| status | ENUM(shipmentstatus) | NULL | planned/in_transit/delivered/cancelled |
| carrier | VARCHAR | NULL | Carrier name |
| tracking_number | VARCHAR | NULL | Tracking number |
| extra_metadata | JSON | NULL | Additional data |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |
| updated_at | TIMESTAMP WITH TZ | NULL | Update timestamp |

**Relationships**:
- FK: organization_id → organizations
- FK: route_id → routes (which links to origin/destination facilities)

**KG Insight**: Properties on the route relationship with time series data

---

## 8. FACILITY_ENVIRONMENTAL_DATA
**Purpose**: Earth observation data for facilities (from Sentinel-5P)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | VARCHAR | NOT NULL | Primary Key |
| facility_id | VARCHAR | NOT NULL | FK → facilities |
| organization_id | VARCHAR | NULL | FK → organizations |
| captured_at | TIMESTAMP | NOT NULL | Data capture timestamp |
| no2_value | DOUBLE PRECISION | NULL | Nitrogen Dioxide |
| co_value | DOUBLE PRECISION | NULL | Carbon Monoxide |
| ch4_value | DOUBLE PRECISION | NULL | Methane |
| so2_value | DOUBLE PRECISION | NULL | Sulfur Dioxide |
| hcho_value | DOUBLE PRECISION | NULL | Formaldehyde |
| aod_value | DOUBLE PRECISION | NULL | Aerosol Optical Depth |
| o3_value | DOUBLE PRECISION | NULL | Ozone |
| aqi_score | DOUBLE PRECISION | NULL | Air Quality Index |
| pollution_level | VARCHAR | NULL | good/moderate/unhealthy/hazardous |
| created_at | TIMESTAMP WITH TZ | NULL | Creation timestamp |

**Relationships**:
- FK: facility_id → facilities
- FK: organization_id → organizations

**KG Insight**: Time series properties on Facility nodes for ESG analysis

---

## ENUMS

### facilitytype
- `warehouse`
- `manufacturing`
- `distribution_center`
- `retail`

### transportmode
- `road_truck`
- `rail_freight`
- `sea_container`
- `air_freight`

### shipmentstatus
- `planned`
- `in_transit`
- `delivered`
- `cancelled`

---

## KNOWLEDGE GRAPH STRUCTURE

### Node Types (8):
1. **Organization** (from organizations)
2. **Facility** (from facilities)
3. **Supplier** (from suppliers)
4. **Product** (from products)
5. **PurchaseOrder** (from purchase_orders)
6. **Route** (from routes - can be relationship OR node)
7. **Shipment** (from shipments - can be properties on Route relationship)
8. **EnvironmentalData** (from facility_environmental_data - properties on Facility)

### Relationship Types:
1. **BELONGS_TO**: All entities → Organization
2. **SUPPLIES**: Supplier → Product
3. **PURCHASES**: Facility → Product (via PurchaseOrder)
4. **ORDERED_FROM**: PurchaseOrder → Supplier
5. **SHIPS_TO**: PurchaseOrder → Facility
6. **CONTAINS**: PurchaseOrder → Product
7. **CONNECTS**: Route linking Facility → Facility
8. **HAS_ROUTE**: Facility → Route → Facility
9. **SHIPPED_ON**: Shipment → Route
10. **HAS_ENVIRONMENTAL_DATA**: Facility → EnvironmentalData (time series)

### Key ESG Metrics for KG:
- **Emissions**: total_emissions_kg_co2, emission_factor, carbon_intensity_per_unit
- **Environmental**: NO2, CO, CH4, SO2, AQI scores
- **Supplier ESG**: tier_level, certifications, sustainability_score
- **Transport**: transport_mode, distance_km, carrier efficiency
- **Cost**: unit_transportation_cost, total_cost

---

## DATA FLOW FOR KG CREATION

```
PostgreSQL (Source of Truth)
    ↓
    ETL Process (to be built)
    ↓
Neo4j Knowledge Graph
    ↓
    Graph Queries & Analytics
    ↓
    Frontend Dashboard
```

**All data modifications happen in PostgreSQL first, then propagate to Neo4j KG.**

---

## NEXT STEPS FOR KG IMPLEMENTATION

1. ✅ **PostgreSQL Schema** - COMPLETE
2. ⏳ **ETL Pipeline** - Build Python scripts to sync PostgreSQL → Neo4j
3. ⏳ **Neo4j Schema Design** - Define node labels and relationship types
4. ⏳ **Cypher Queries** - Build analytical queries for ESG insights
5. ⏳ **Frontend Integration** - Visualize KG in the Knowledge Graph page

---

**Generated**: 2025-10-29
**Database**: veriearth (PostgreSQL + PostGIS)
**Total Tables**: 8 main entities + auth tables
**Purpose**: ESG Supply Chain Knowledge Graph

