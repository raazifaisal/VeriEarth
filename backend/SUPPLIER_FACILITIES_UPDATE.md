# Supplier-Owned Facilities Update

## ✅ **Completed Changes**

### 1. **Test Data Updated** (`test_data_small/`)

#### **Facilities CSV** - Added `supplier_id` column
- **Your Facilities** (4 facilities):
  - F001: Mumbai Warehouse (VeriEarth Corp)
  - F002: Delhi Distribution Center (VeriEarth Corp)
  - F003: Bangalore Factory (VeriEarth Corp)
  - F004: Chennai Port (VeriEarth Corp)

- **Supplier Facilities** (4 new facilities):
  - F101: ABC Steel Plant (SUP001 - ABC Materials Ltd)
  - F102: ABC Metal Foundry (SUP001 - ABC Materials Ltd)
  - F103: XYZ Electronics Factory (SUP002 - XYZ Logistics)
  - F104: Global Parts Manufacturing (SUP003 - Global Parts Inc)

#### **Routes CSV** - Updated to reflect supplier → your facility flow
- R101: F101 (ABC Steel Plant) → F001 (Mumbai Warehouse)
- R102: F102 (ABC Foundry) → F004 (Chennai Port)
- R103: F103 (XYZ Electronics) → F002 (Delhi DC)
- R104: F104 (Global Parts) → F003 (Bangalore Factory)

#### **Shipments CSV** - Updated origins to supplier facilities
- S001: F101 → F001 (ABC Steel Plant to Mumbai Warehouse)
- S002: F103 → F002 (XYZ Electronics to Delhi DC)
- S003: F104 → F003 (Global Parts to Bangalore Factory)
- S004: F102 → F004 (ABC Foundry to Chennai Port)
- S005: F103 → F001 (XYZ Electronics to Mumbai Warehouse)

---

### 2. **Database Schema Updated**

#### **Facilities Table** - Added `supplier_id` column
```sql
ALTER TABLE facilities ADD COLUMN supplier_id VARCHAR;
ALTER TABLE facilities ADD CONSTRAINT facilities_supplier_id_fkey 
  FOREIGN KEY (supplier_id) REFERENCES suppliers(id);
```

**Column Details:**
- `supplier_id` (VARCHAR, nullable)
- Foreign key to `suppliers.id`
- NULL = facility owned by your organization
- NOT NULL = facility owned by supplier

#### **Alembic Migration**
- File: `alembic/versions/add_supplier_id_to_facilities_manual.py`
- Revision ID: `add_supplier_id_manual`
- Status: ✅ Applied successfully

---

### 3. **Backend Models Updated**

#### **db/models.py** - `Facility` model
```python
class Facility(Base):
    __tablename__ = 'facilities'
    # ... existing fields ...
    supplier_id = Column(String, ForeignKey('suppliers.id'), nullable=True)
```

#### **db/supply_chain_schemas.py** - `FacilityCreate` schema
```python
class FacilityCreate(BaseModel):
    # ... existing fields ...
    supplier_id: Optional[str] = None  # If facility is owned by a supplier
```

#### **services/supply_chain_service.py** - `create_facility` method
```python
def create_facility(self, payload: FacilityCreate, custom_id: str = None) -> Facility:
    pg_facility = Facility(
        # ... existing fields ...
        supplier_id=payload.supplier_id,  # Added
    )
```

#### **ingestion/loader.py** - `load_facilities` function
```python
payload = FacilityCreate(
    # ... existing fields ...
    supplier_id=r.get("supplier_id") if r.get("supplier_id") else None,
)
```

---

### 4. **Documentation Created**

- `test_data_small/DATA_STRUCTURE.md` - Complete data structure overview
- `SUPPLIER_FACILITIES_UPDATE.md` - This file

---

## 🎯 **What This Enables**

### 1. **Realistic Supply Chain Model**
```
SUPPLIER FACILITY (manufacturing) → YOUR FACILITY (distribution) → CUSTOMERS
     F101 (ABC Steel Plant)       →     F001 (Mumbai Warehouse)     →   End Users
```

### 2. **Factory-Level Pollution Tracking**
- Track EO data at **supplier manufacturing facilities** (where production happens)
- Compare pollution between different supplier factories
- Identify which suppliers have cleaner manufacturing processes

### 3. **Multi-Facility Supplier Analysis**
- **ABC Materials Ltd** has 2 facilities:
  - F101 (Steel Plant)
  - F102 (Metal Foundry)
- Can compare their pollution and efficiency

### 4. **Complete Supply Chain Visibility**
```sql
-- Get complete supply chain with supplier factory pollution
SELECT 
    s.name as supplier_name,
    sf.name as supplier_facility_name,
    sf_eo.aqi_score as supplier_factory_aqi,
    p.name as product_name,
    yf.name as your_facility_name,
    yf_eo.aqi_score as your_facility_aqi
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.id
JOIN facilities sf ON sf.supplier_id = s.id  -- Supplier factory
JOIN products p ON po.product_id = p.id
JOIN facilities yf ON po.facility_id = yf.id  -- Your facility
LEFT JOIN facility_environmental_data sf_eo ON sf_eo.facility_id = sf.id
LEFT JOIN facility_environmental_data yf_eo ON yf_eo.facility_id = yf.id
WHERE po.organization_id = 'YOUR_ORG';
```

---

## 📊 **Next Steps**

### 1. **Ingest the Updated Test Data**
```bash
# Clear existing data first
# Then import all entities in order:
1. Suppliers
2. Facilities (including supplier facilities)
3. Products
4. Routes (supplier facility → your facility)
5. Shipments (supplier facility → your facility)
6. Purchase Orders
```

### 2. **Enrich Supplier Facilities with EO Data**
- Run EO enrichment for supplier-owned facilities (F101, F102, F103, F104)
- Track pollution at manufacturing sites (most important for ESG!)

### 3. **Update Frontend Data Management**
- Display `supplier_id` column in facilities table
- Show "Owner Company" (VeriEarth Corp vs ABC Materials Ltd)
- Filter: "My Facilities" vs "Supplier Facilities"
- Add "Supplier Name" column for supplier-owned facilities

### 4. **Build Analytics Queries**
```sql
-- Compare supplier factory pollution
SELECT 
    s.name as supplier,
    f.name as factory,
    AVG(f_eo.aqi_score) as avg_aqi,
    COUNT(po.po_id) as num_orders,
    SUM(po.total_cost) as total_spent
FROM suppliers s
JOIN facilities f ON f.supplier_id = s.id
LEFT JOIN facility_environmental_data f_eo ON f_eo.facility_id = f.id
LEFT JOIN purchase_orders po ON po.supplier_id = s.id
GROUP BY s.id, s.name, f.id, f.name
ORDER BY avg_aqi ASC;
```

### 5. **Build Neo4j Knowledge Graph**
```cypher
// Create relationships
(Supplier)-[:OWNS]->(SupplierFacility)
(SupplierFacility)-[:MANUFACTURES]->(Product)
(Shipment)-[:SHIPS_FROM]->(SupplierFacility)
(Shipment)-[:SHIPS_TO]->(YourFacility)
(Shipment)-[:USES_ROUTE]->(Route)
```

---

## 🎉 **Benefits**

### **Before:**
- ❌ Suppliers were just lat/lon points
- ❌ No visibility into supplier manufacturing
- ❌ Couldn't track pollution at production source
- ❌ No factory-level comparison

### **After:**
- ✅ Suppliers have actual manufacturing facilities
- ✅ Track pollution where products are made
- ✅ Compare multiple factories from same supplier
- ✅ Realistic supply chain from production to distribution
- ✅ Full Scope 3 emissions visibility
- ✅ Better supplier selection based on factory pollution

---

## 💡 **Example Use Case**

### **Question**: Which supplier has cleaner manufacturing for Steel Rods?

**Scenario**:
- **Supplier A** (ABC Materials): Factory AQI = 145 (Unhealthy)
- **Supplier B** (XYZ Metals): Factory AQI = 98 (Moderate)

**Decision**: Pay 5% more for Supplier B to reduce supply chain pollution by 32%

**VeriEarth Value**: Data-driven ESG supplier selection! 🌱

---

## 🔧 **Technical Details**

### **Database Constraints**
- `facilities.supplier_id` is **optional** (nullable)
- If NULL → facility owned by your organization
- If NOT NULL → facility owned by supplier (foreign key to `suppliers.id`)
- Both types of facilities share same organization_id for access control

### **Foreign Key Cascade**
- Deleting a supplier → Cannot delete if they have facilities (integrity error)
- This is intentional to prevent data loss
- Must delete/reassign facilities before deleting supplier

### **Data Ingestion**
- CSV loader automatically handles `supplier_id` field
- If field is empty → NULL (your facility)
- If field has value → Sets supplier_id (supplier facility)

---

## ✅ **Status: READY FOR TESTING**

All code changes have been applied and the migration has been successfully executed. You can now:
1. Ingest the updated test data
2. View supplier-owned facilities in the database
3. Enrich supplier facilities with EO data
4. Build analytics to compare supplier factory pollution


