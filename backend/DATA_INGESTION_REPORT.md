# VeriEarth Data Ingestion Report

**Date:** January 28, 2025  
**System:** VeriEarth Supply Chain Carbon Tracking Platform  
**Status:** Active and Operational

---

## 📊 Overview

VeriEarth ingests and tracks multiple data types to provide comprehensive supply chain carbon and environmental monitoring. The system supports both **structured supply chain data** and **satellite-derived environmental data**.

---

## 🔄 Data Ingestion Pipeline

### 1. **Supply Chain Entities** (PostgreSQL + Neo4j)

#### A. **Suppliers**
- **Source:** CSV uploads, ERP systems
- **Format:** 
  - `supplier_id`: Unique identifier
  - `name`: Supplier name
  - `contact_info`: Contact details
  - `address`: Physical address
  - `country`: Country code
- **Storage:** 
  - PostgreSQL: `suppliers` table
  - Neo4j: `Supplier` nodes
- **Auto-enrichment:** Location geocoding

#### B. **Facilities**
- **Source:** CSV uploads, Facility databases
- **Format:**
  - `facility_id`: Unique identifier (auto-generated if missing)
  - `name`: Facility name
  - `facility_type`: warehouse, port, factory, distribution_center
  - `location`: Latitude/Longitude (required)
  - `address`: Physical address
  - `capacity`: Capacity metrics
- **Storage:**
  - PostgreSQL: `facilities` table (with PostGIS Point geometry)
  - Neo4j: `Facility` nodes
- **Auto-enrichment:** 
  - EO data fetching (pollutants, AQI)
  - Auto-creation of routes between facilities

#### C. **Routes**
- **Source:** CSV uploads, Auto-generated from shipments
- **Format:**
  - `route_id`: Unique identifier
  - `origin_facility_id`: Starting facility
  - `destination_facility_id`: End facility
  - `transport_mode`: road_truck, road_van, rail_freight, air_cargo, sea_container, sea_bulk, pipeline
  - `distance_km`: Distance in kilometers
  - `duration_hours`: Travel time
  - `emission_factor_kg_co2_per_ton_km`: Emission factor
- **Storage:**
  - PostgreSQL: `routes` table
  - Neo4j: `ROUTE` relationships between facilities
- **Auto-generation:** Routes are automatically created from shipments if missing

#### D. **Shipments**
- **Source:** CSV uploads, ERP tracking data
- **Format:**
  - `shipment_id`: Unique identifier
  - `route_id`: Associated route (auto-created if missing)
  - `weight_kg`: Shipment weight
  - `volume_m3`: Shipment volume
  - `cost_per_kg`: Unit cost
  - `total_cost`: Total shipment cost
  - `emission_factor_kg_co2_per_ton_km`: CO2 emission factor
  - `emissions_per_kg`: Emissions per kilogram
  - `total_emissions_kg_co2`: Total CO2 emissions (calculated)
  - `shipment_date`: Date shipped
  - `planned_delivery_date`: Expected delivery
  - `actual_delivery_date`: Actual delivery date
  - `status`: planned, in_transit, delivered, cancelled
- **Storage:**
  - PostgreSQL: `shipments` table
  - Neo4j: `SHIPMENT` relationships
- **CO2 Calculation:**
  ```
  CO2 = (distance_km × weight_kg × emission_factor_kg_co2_per_ton_km) / 1000
  ```

---

### 2. **Environmental Data** (Satellite EO via Google Earth Engine)

#### **Pollutant Measurements** (7 Pollutants)
- **Source:** Google Earth Engine API
- **Satellite Platforms:**
  - Copernicus Sentinel-5P
  - MODIS Terra/Aqua
- **Update Frequency:** Monthly aggregations
- **Spatial Resolution:** ~1km (AOI-based, 5km buffer around facilities)

##### **Tracked Pollutants:**

| Pollutant | Dataset | Band | Purpose |
|-----------|---------|------|---------|
| **NO2** | COPERNICUS/S5P/OFFL/L3_NO2 | NO2_column_number_density | Air Quality, Industrial Activity |
| **CO** | COPERNICUS/S5P/OFFL/L3_CO | CO_column_number_density | Air Quality, CO2 Proxy |
| **HCHO** | COPERNICUS/S5P/OFFL/L3_HCHO | tropospheric_HCHO_column_number_density | Formaldehyde, Carcinogen |
| **CH4** | COPERNICUS/S5P/OFFL/L3_CH4 | CH4_column_volume_mixing_ratio_dry_air | Greenhouse Gas (28x CO2) |
| **SO2** | COPERNICUS/S5P/OFFL/L3_SO2 | SO2_column_number_density | Air Quality, Acid Rain |
| **AOD** | MODIS/061/MCD19A2_GRANULES | Optical_Depth_047 | Aerosol Optical Depth, Air Quality |
| **O3** | COPERNICUS/S5P/OFFL/L3_O3 | O3_column_number_density | Ozone, Smog Indicator |

##### **Storage:**
- **PostgreSQL:** `facility_environmental_data` table
  - Columns: `no2_value`, `co_value`, `hcho_value`, `ch4_value`, `so2_value`, `aod_value`, `o3_value`
  - Timestamped: `captured_at`
  - Aggregated metrics: `aqi_score`, `pollution_level`
- **Neo4j:** `EnvironmentalSnapshot` nodes linked to facilities

##### **Data Processing:**
1. Fetch 3 months of historical data
2. Compute monthly averages for each pollutant
3. Calculate AQI score (Air Quality Index)
4. Categorize pollution level: `good`, `moderate`, `unhealthy_sensitive`, `unhealthy`, `hazardous`

---

## 🌍 Carbon Emissions Tracking

### **CO2 Emissions** (Activity-Based Calculation)
- **NOT satellite-based** (CO2 not reliably measurable from satellites)
- **Calculation Method:** Activity data × emission factors
- **Formula:** 
  ```python
  CO2_emissions_kg = (distance_km × weight_kg × emission_factor_kg_co2_per_ton_km) / 1000
  ```
- **Emission Factors by Transport Mode:**
  - Road Truck: ~0.062 kg CO2/ton-km
  - Sea Container: ~0.020 kg CO2/ton-km
  - Air Cargo: ~1.880 kg CO2/ton-km
  - Rail Freight: ~0.022 kg CO2/ton-km
  - Road Van: ~0.080 kg CO2/ton-km
  - Sea Bulk: ~0.015 kg CO2/ton-km
  - Pipeline: ~0.010 kg CO2/ton-km

### **CO2e (Carbon Dioxide Equivalent)**
- **Components:**
  - CO2 (calculated from activity data)
  - CH4 (from satellite EO data) - 28x warming potential
- **Note:** N2O not currently tracked (would require additional satellite data)

---

## 📝 Supported Data Formats

### **CSV Upload**
- **Endpoint:** `POST /api/ingestion/upload`
- **Required columns** (entity-specific):
  - **Suppliers:** supplier_id, name, address, country
  - **Facilities:** facility_id, name, facility_type, latitude, longitude
  - **Routes:** route_id, origin_facility_id, destination_facility_id, transport_mode, distance_km
  - **Shipments:** shipment_id, route_id, weight_kg, total_cost, shipment_date
- **Auto-handling:**
  - Missing facility_ids → auto-generated from name
  - Missing route_ids → auto-created from shipment data
  - Missing transport_mode → defaults to "road_truck"
  - Missing organizations → auto-created

### **JSON API**
- **Endpoints:**
  - `POST /api/suppliers` - Create supplier
  - `POST /api/facilities` - Create facility
  - `POST /api/routes` - Create route
  - `POST /api/shipments` - Create shipment
  - `POST /api/facilities/{id}/enrich-eo` - Manual EO enrichment

### **Multi-Organization Support**
- All entities include `organization_id`
- Data isolation by organization
- Multi-tenant compatible

---

## 🔄 Data Flow Architecture

```
1. CSV Upload → Ingestion API
   ↓
2. Header Mapping & Validation
   ↓
3. Data Normalization
   ↓
4. PostgreSQL Storage (Primary)
   ↓
5. Auto-enrichment (EO data fetch)
   ↓
6. Neo4j Graph Building (deferred)
```

---

## 🚀 Key Features

### **Automatic Behaviors:**
- ✅ Auto-create missing facilities from names
- ✅ Auto-create routes from shipments
- ✅ Auto-geocode addresses for facilities
- ✅ Auto-fetch EO data for facilities with coordinates
- ✅ Auto-create organizations if missing
- ✅ Default transport modes and emission factors

### **Smart Defaults:**
- Missing `transport_mode` → `road_truck`
- Missing `facility_id` → Generated from `name` (lowercased, space-replaced)
- Missing `route_id` → Created from shipment origin/dest/transport
- Missing `emission_factor` → Uses default for transport mode

---

## 📈 Data Quality & Validation

- **Foreign Key Integrity:** Automatic handling of missing relationships
- **Coordinate Validation:** Latitude (-90 to 90), Longitude (-180 to 180)
- **Required Fields:** Enforced at database level
- **Data Types:** Strict validation (Floats, Dates, Enums)
- **Duplicate Handling:** Skip duplicates, preserve unique IDs

---

## 🔐 Data Security & Isolation

- **Organization-based isolation:** All queries filtered by `organization_id`
- **Multi-tenant architecture:** Safe for enterprise use
- **No cross-organization data leakage**

---

## 📊 Current Data Statistics

- **Suppliers:** Unlimited
- **Facilities:** Unlimited (with geospatial indexing)
- **Routes:** Unlimited (with graph relationships)
- **Shipments:** Unlimited (with CO2 tracking)
- **EO Data Points:** Timestamped, facility-linked
- **Pollutants Tracked:** 7 (NO2, CO, HCHO, CH4, SO2, AOD, O3)

---

## 🎯 Use Cases Enabled

1. **Carbon Footprint Tracking:** Track CO2 emissions across supply chain
2. **Air Quality Monitoring:** Monitor pollutant levels at facilities
3. **Route Optimization:** Find lowest-emission paths (Neo4j graph queries)
4. **Compliance Reporting:** Generate GHG Protocol-compliant reports
5. **Supplier Transparency:** Track environmental performance
6. **Risk Assessment:** Identify high-pollution facilities

---

## 🔧 Technical Stack

- **Database:** PostgreSQL 15+ with PostGIS
- **Graph DB:** Neo4j 5+
- **EO Engine:** Google Earth Engine API
- **API:** FastAPI with async support
- **Orchestration:** Docker/Podman Compose
- **Migrations:** Alembic

---

**Last Updated:** January 28, 2025  
**Version:** 1.0  
**Status:** Production Ready ✅
