# Test Data Structure (Small Dataset)

## Overview
This dataset demonstrates a realistic supply chain where **suppliers own manufacturing facilities** that produce goods, which are then shipped to **your facilities** (VeriEarth Corp) for distribution.

---

## 🏢 **YOUR FACILITIES (VeriEarth Corp)**

| ID   | Name                        | Type                  | Location            | Capacity | supplier_id |
|------|-----------------------------|-----------------------|---------------------|----------|-------------|
| F001 | Mumbai Warehouse            | warehouse             | Mumbai, India       | 1000t    | NULL        |
| F002 | Delhi Distribution Center   | distribution_center   | Delhi, India        | 800t     | NULL        |
| F003 | Bangalore Factory           | manufacturing         | Bangalore, India    | 1200t    | NULL        |
| F004 | Chennai Port                | warehouse             | Chennai, India      | 2000t    | NULL        |

---

## 🏭 **SUPPLIER FACILITIES (Supplier-Owned Manufacturing)**

| ID   | Name                        | Type          | Owner Company       | supplier_id | Location            | Capacity |
|------|-----------------------------|---------------|---------------------|-------------|---------------------|----------|
| F101 | ABC Steel Plant             | manufacturing | ABC Materials Ltd   | SUP001      | Mumbai, India       | 5000t    |
| F102 | ABC Metal Foundry           | manufacturing | ABC Materials Ltd   | SUP001      | Mumbai, India       | 3000t    |
| F103 | XYZ Electronics Factory     | manufacturing | XYZ Logistics       | SUP002      | Delhi, India        | 2000t    |
| F104 | Global Parts Manufacturing  | manufacturing | Global Parts Inc    | SUP003      | Bangalore, India    | 4000t    |

---

## 📦 **SUPPLY CHAIN FLOW**

### Supply Chain Path 1: Steel Rods
```
SUP001 (ABC Materials Ltd)
  ↓ manufactures at
F101 (ABC Steel Plant, Mumbai)
  ↓ ships via R101 (road truck, 5km)
F001 (Mumbai Warehouse, VeriEarth Corp)
  ↓ distributes to customers
```
**Shipment**: S001 (5000 kg Steel Rods)
**Purchase Order**: PO001 (100 units @ $500 = $50,000)
**Product**: P001 (Steel Rods)

---

### Supply Chain Path 2: Electronic Components
```
SUP002 (XYZ Logistics)
  ↓ manufactures at
F103 (XYZ Electronics Factory, Delhi)
  ↓ ships via R103 (road truck, 2km)
F002 (Delhi Distribution Center, VeriEarth Corp)
  ↓ distributes to customers
```
**Shipment**: S002 (100 kg Electronic Components)
**Purchase Order**: PO002 (200 units @ $25 = $5,000)
**Product**: P002 (Electronic Components)

---

### Supply Chain Path 3: Plastic Containers
```
SUP003 (Global Parts Inc)
  ↓ manufactures at
F104 (Global Parts Manufacturing, Bangalore)
  ↓ ships via R104 (road truck, 3km)
F003 (Bangalore Factory, VeriEarth Corp)
  ↓ distributes to customers
```
**Shipment**: S003 (100 kg Plastic Containers)
**Purchase Order**: PO003 (50 units @ $100 = $5,000)
**Product**: P003 (Plastic Containers)

---

### Supply Chain Path 4: Raw Materials
```
SUP001 (ABC Materials Ltd)
  ↓ manufactures at
F102 (ABC Metal Foundry, Mumbai)
  ↓ ships via R102 (sea container, 1330km)
F004 (Chennai Port, VeriEarth Corp)
  ↓ distributes to customers
```
**Shipment**: S004 (1000 kg Raw Materials)
**Purchase Order**: PO004 (1000 units @ $10 = $10,000)
**Product**: P004 (Raw Materials)

---

### Supply Chain Path 5: Finished Goods
```
SUP002 (XYZ Logistics)
  ↓ manufactures at
F103 (XYZ Electronics Factory, Delhi)
  ↓ ships via R103 (rail freight, 1407km)
F001 (Mumbai Warehouse, VeriEarth Corp)
  ↓ distributes to customers
```
**Shipment**: S005 (750 kg Finished Goods)
**Purchase Order**: PO005 (75 units @ $200 = $15,000)
**Product**: P005 (Finished Goods)

---

## 🎯 **ESG Tracking Implications**

### 1. **Supplier Factory Pollution** (Most Important)
Track EO data at supplier manufacturing facilities:
- **F101**: ABC Steel Plant pollution (manufacturing steel)
- **F102**: ABC Metal Foundry pollution (processing raw materials)
- **F103**: XYZ Electronics Factory pollution (electronics assembly)
- **F104**: Global Parts Manufacturing pollution (parts production)

### 2. **Transportation Emissions**
Calculate emissions for routes FROM supplier facilities TO your facilities:
- **R101**: F101 → F001 (5km, road truck, local delivery)
- **R102**: F102 → F004 (1330km, sea container, long distance)
- **R103**: F103 → F002 (2km, road truck, local delivery)
- **R104**: F104 → F003 (3km, road truck, local delivery)

### 3. **Your Facility Pollution** (Minor)
Track EO data at your distribution/warehouse facilities:
- **F001**: Mumbai Warehouse (storage & distribution)
- **F002**: Delhi DC (distribution center)
- **F003**: Bangalore Factory (assembly/packaging)
- **F004**: Chennai Port (import/export hub)

---

## 📊 **Key Insights**

### Multi-Facility Suppliers
- **ABC Materials Ltd (SUP001)** owns 2 facilities:
  - F101 (Steel Plant) - produces Steel Rods
  - F102 (Metal Foundry) - produces Raw Materials
  - Can compare pollution between their 2 factories!

### Geographic Proximity
Most shipments are local (supplier facility → nearby VeriEarth facility):
- Mumbai → Mumbai (5km)
- Delhi → Delhi (2km)
- Bangalore → Bangalore (3km)
- Only **one** long-distance shipment: Mumbai → Chennai (1330km)

### Facility Types
- **Your facilities**: Mix of warehouse, distribution_center, manufacturing
- **Supplier facilities**: All manufacturing (where actual production happens)
- This reflects reality: suppliers manufacture, you distribute

---

## 🗄️ **Database Schema Update Required**

The `facilities` table now has a **supplier_id** column:
```sql
ALTER TABLE facilities ADD COLUMN supplier_id VARCHAR REFERENCES suppliers(id);
```

**Values:**
- `supplier_id = NULL` → Facility owned by your organization
- `supplier_id = 'SUP001'` → Facility owned by ABC Materials Ltd
- `supplier_id = 'SUP002'` → Facility owned by XYZ Logistics
- `supplier_id = 'SUP003'` → Facility owned by Global Parts Inc

---

## 🔗 **Neo4j Knowledge Graph (Future)**

The complete supply chain relationships will be modeled in Neo4j:

```cypher
// Nodes
(:Supplier {id: 'SUP001', name: 'ABC Materials Ltd'})
(:Facility {id: 'F101', name: 'ABC Steel Plant', type: 'manufacturing'})
(:Product {id: 'P001', name: 'Steel Rods'})
(:PurchaseOrder {id: 'PO001', quantity: 100, total_cost: 50000})
(:Facility {id: 'F001', name: 'Mumbai Warehouse', type: 'warehouse'})
(:Shipment {id: 'S001', weight_kg: 5000})
(:Route {id: 'R101', distance_km: 5})

// Relationships
(SUP001)-[:OWNS]->(F101)
(F101)-[:MANUFACTURES]->(P001)
(SUP001)-[:SUPPLIES]->(P001)
(PO001)-[:ORDERS_FROM]->(SUP001)
(PO001)-[:ORDERS_PRODUCT]->(P001)
(PO001)-[:DELIVERS_TO]->(F001)
(S001)-[:SHIPS_FROM]->(F101)
(S001)-[:SHIPS_TO]->(F001)
(S001)-[:USES_ROUTE]->(R101)
(S001)-[:FULFILLS]->(PO001)
```

---

## ✅ **Next Steps**

1. **Update database schema**: Add `supplier_id` column to `facilities` table
2. **Update loader logic**: Handle supplier-owned facilities in ingestion
3. **Update frontend**: Show supplier name for supplier-owned facilities
4. **Enrich supplier facilities with EO data**: Track pollution at manufacturing sites
5. **Build Neo4j graph**: Create complete supply chain knowledge graph
6. **Analytics**: Compare supplier factory pollution, optimize supplier selection


