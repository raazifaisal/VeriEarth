# Knowledge Graph Snapshot (Org-scoped Cypher Checklist)

Set your org id first:

```cypher
:param org => 'ecfc141e-2e55-4670-bb8e-9e8813b02866';
```

## 1) Sanity and Inventory

- Verify Organization node
```cypher
MATCH (o:Organization {id:$org})
RETURN o.id AS id, o.name AS name, labels(o) AS labels;
```
╒══════════════════════════════════════╤════════════╤════════════════╕
│id                                    │name        │labels          │
╞══════════════════════════════════════╪════════════╪════════════════╡
│"ecfc141e-2e55-4670-bb8e-9e8813b02866"│"Test Org 1"│["Organization"]│
└──────────────────────────────────────┴────────────┴────────────────┘

- Node counts by label (org-scoped)
```cypher
CALL {
  MATCH (n:Facility {org_id:$org})      RETURN 'Facility'      AS label, count(n) AS c
  UNION ALL
  MATCH (n:Route {org_id:$org})         RETURN 'Route'         AS label, count(n) AS c
  UNION ALL
  MATCH (n:Shipment {org_id:$org})      RETURN 'Shipment'      AS label, count(n) AS c
  UNION ALL
  MATCH (n:Supplier {org_id:$org})      RETURN 'Supplier'      AS label, count(n) AS c
  UNION ALL
  MATCH (n:Product {org_id:$org})       RETURN 'Product'       AS label, count(n) AS c
  UNION ALL
  MATCH (n:PurchaseOrder {org_id:$org}) RETURN 'PurchaseOrder' AS label, count(n) AS c
  UNION ALL
  MATCH (n:EOReading {org_id:$org})     RETURN 'EOReading'     AS label, count(n) AS c
}
RETURN label, c ORDER BY label;
```
╒═══════════════╤═══╕
│label          │c  │
╞═══════════════╪═══╡
│"EOReading"    │98 │
├───────────────┼───┤
│"Facility"     │14 │
├───────────────┼───┤
│"Product"      │10 │
├───────────────┼───┤
│"PurchaseOrder"│20 │
├───────────────┼───┤
│"Route"        │21 │
├───────────────┼───┤
│"Shipment"     │20 │
├───────────────┼───┤
│"Supplier"     │6  │
└───────────────┴───┘

- Relationship counts by type (org-scoped)
```cypher
CALL {
  MATCH (:Organization {id:$org})-[:HAS_SUPPLIER]->(:Supplier {org_id:$org})
  RETURN 'HAS_SUPPLIER' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Organization {id:$org})-[:HAS_FACILITY]->(:Facility {org_id:$org})
  RETURN 'HAS_FACILITY' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Supplier {org_id:$org})-[:OWNS]->(:Facility {org_id:$org})
  RETURN 'OWNS' AS rel, count(*) AS c
  UNION ALL
  MATCH (:PurchaseOrder {org_id:$org})-[:FOR_PRODUCT]->(:Product {org_id:$org})
  RETURN 'FOR_PRODUCT' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Supplier {org_id:$org})-[:RECEIVES_PO]->(:PurchaseOrder {org_id:$org})
  RETURN 'RECEIVES_PO' AS rel, count(*) AS c
  UNION ALL
  MATCH (:PurchaseOrder {org_id:$org})-[:FULFILLED_AT]->(:Facility {org_id:$org})
  RETURN 'FULFILLED_AT' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Facility {org_id:$org})<-[:ORIGIN]-(:Route {org_id:$org})-[:DESTINATION]->(:Facility {org_id:$org})
  RETURN 'ORIGIN/DESTINATION (paired)' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Shipment {org_id:$org})-[:USES_ROUTE]->(:Route {org_id:$org})
  RETURN 'USES_ROUTE' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Shipment {org_id:$org})-[:BELONGS_TO]->(:Organization {id:$org})
  RETURN 'BELONGS_TO' AS rel, count(*) AS c
  UNION ALL
  MATCH (:Facility {org_id:$org})-[:HAS_EO_READING]->(:EOReading {org_id:$org})
  RETURN 'HAS_EO_READING' AS rel, count(*) AS c
}
RETURN rel, c ORDER BY rel;
```
╒════════════════╤═══╕
│rel             │c  │
╞════════════════╪═══╡
│"BELONGS_TO"    │20 │
├────────────────┼───┤
│"FOR_PRODUCT"   │20 │
├────────────────┼───┤
│"FULFILLED_AT"  │20 │
├────────────────┼───┤
│"HAS_EO_READING"│98 │
├────────────────┼───┤
│"HAS_FACILITY"  │14 │
├────────────────┼───┤
│"HAS_SUPPLIER"  │6  │
├────────────────┼───┤
│"OWNS"          │7  │
├────────────────┼───┤
│"RECEIVES_PO"   │20 │
├────────────────┼───┤
│"USES_ROUTE"    │20 │
└────────────────┴───┘

- Quick samples
```cypher
MATCH (f:Facility {org_id:$org})
RETURN f.id AS id, f.name AS name, f.city AS city, f.country AS country
LIMIT 10;
```
╒══════╤═══════════════════════════╤═══════════╤═══════╕
│id    │name                       │city       │country│
╞══════╪═══════════════════════════╪═══════════╪═══════╡
│"F107"│"Pune Metal Works"         │"Pune"     │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F108"│"Hydera Plastics Plant"    │"Hyderabad"│"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F109"│"Eastern Electronics Plant"│"Kolkata"  │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F007"│"Kolkata Warehouse"        │"Kolkata"  │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F001"│"Mumbai Warehouse"         │"Mumbai"   │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F002"│"Delhi Distribution Center"│"Delhi"    │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F003"│"Bangalore Factory"        │"Bangalore"│"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F004"│"Chennai Port"             │"Chennai"  │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F101"│"ABC Steel Plant"          │"Mumbai"   │"India"│
├──────┼───────────────────────────┼───────────┼───────┤
│"F102"│"ABC Metal Foundry"        │"Mumbai"   │"India"│
└──────┴───────────────────────────┴───────────┴───────┘

```cypher
MATCH (r:Route {org_id:$org})
RETURN r.id AS id, r.transport_mode AS mode, r.distance_km AS km, r.duration_hours AS h
LIMIT 10;
```
╒══════╤═══════════════╤══════╤════╕
│id    │mode           │km    │h   │
╞══════╪═══════════════╪══════╪════╡
│"R001"│"ROAD_TRUCK"   │1407.0│18.0│
├──────┼───────────────┼──────┼────┤
│"R002"│"ROAD_TRUCK"   │850.0 │12.0│
├──────┼───────────────┼──────┼────┤
│"R003"│"ROAD_TRUCK"   │1740.0│22.0│
├──────┼───────────────┼──────┼────┤
│"R004"│"SEA_CONTAINER"│1330.0│35.0│
├──────┼───────────────┼──────┼────┤
│"R005"│"RAIL_FREIGHT" │1407.0│14.0│
├──────┼───────────────┼──────┼────┤
│"R101"│"ROAD_TRUCK"   │120.0 │3.0 │
├──────┼───────────────┼──────┼────┤
│"R102"│"SEA_CONTAINER"│1330.0│35.0│
├──────┼───────────────┼──────┼────┤
│"R103"│"ROAD_TRUCK"   │65.0  │1.5 │
├──────┼───────────────┼──────┼────┤
│"R104"│"ROAD_TRUCK"   │180.0 │4.0 │
├──────┼───────────────┼──────┼────┤
│"R105"│"AIR_CARGO"    │1740.0│3.0 │
└──────┴───────────────┴──────┴────┘

```cypher
MATCH (s:Supplier {org_id:$org})
RETURN s.id AS id, s.name AS name, s.tier_level AS tier
LIMIT 10;
```
╒════════╤════════════════════════╤════════╕
│id      │name                    │tier    │
╞════════╪════════════════════════╪════════╡
│"SUP001"│"ABC Materials Ltd"     │"tier_1"│
├────────┼────────────────────────┼────────┤
│"SUP002"│"XYZ Logistics"         │"tier_2"│
├────────┼────────────────────────┼────────┤
│"SUP003"│"Global Parts Inc"      │"tier_1"│
├────────┼────────────────────────┼────────┤
│"SUP004"│"Pune Metals Pvt Ltd"   │"tier_2"│
├────────┼────────────────────────┼────────┤
│"SUP005"│"Hydera Plastics Ltd"   │"tier_2"│
├────────┼────────────────────────┼────────┤
│"SUP006"│"Eastern Electronics Co"│"tier_1"│
└────────┴────────────────────────┴────────┘

```cypher
MATCH (e:EOReading {org_id:$org})
RETURN e.id AS id, e.facility_id AS fid, e.observed_at AS ts, e.aqi_score AS aqi
LIMIT 10;
```
╒═══════════════╤══════╤════════════╤═════╕
│id             │fid   │ts          │aqi  │
╞═══════════════╪══════╪════════════╪═════╡
│"F001::2025-04"│"F001"│"2025-04-01"│69.9 │
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-05"│"F001"│"2025-05-01"│144.7│
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-06"│"F001"│"2025-06-01"│65.7 │
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-07"│"F001"│"2025-07-01"│68.6 │
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-08"│"F001"│"2025-08-01"│137.3│
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-09"│"F001"│"2025-09-01"│86.8 │
├───────────────┼──────┼────────────┼─────┤
│"F001::2025-10"│"F001"│"2025-10-01"│103.3│
├───────────────┼──────┼────────────┼─────┤
│"F002::2025-04"│"F002"│"2025-04-01"│74.8 │
├───────────────┼──────┼────────────┼─────┤
│"F002::2025-05"│"F002"│"2025-05-01"│126.1│
├───────────────┼──────┼────────────┼─────┤
│"F002::2025-06"│"F002"│"2025-06-01"│65.2 │
└───────────────┴──────┴────────────┴─────┘

## 2) Integrity Checks

- Routes connected at both ends
```cypher
MATCH (rt:Route {org_id:$org})
OPTIONAL MATCH (o:Facility {org_id:$org})-[:ORIGIN]->(rt)-[:DESTINATION]->(d:Facility {org_id:$org})
WITH rt, o IS NOT NULL AS hasO, d IS NOT NULL AS hasD
RETURN count(*) AS routes,
       sum(CASE WHEN hasO THEN 1 ELSE 0 END) AS withOrigin,
       sum(CASE WHEN hasD THEN 1 ELSE 0 END) AS withDest,
       sum(CASE WHEN hasO AND hasD THEN 1 ELSE 0 END) AS fullyLinked;
```
╒══════╤══════════╤════════╤═══════════╕
│routes│withOrigin│withDest│fullyLinked│
╞══════╪══════════╪════════╪═══════════╡
│21    │21        │21      │21         │
└──────┴──────────┴────────┴───────────┘

- Shipments link to Route and Org
```cypher
MATCH (sh:Shipment {org_id:$org})
OPTIONAL MATCH (sh)-[:USES_ROUTE]->(rt:Route {org_id:$org})
OPTIONAL MATCH (sh)-[:BELONGS_TO]->(o:Organization {id:$org})
WITH sh, rt IS NOT NULL AS hasRoute, o IS NOT NULL AS hasOrg
RETURN count(*) AS shipments,
       sum(CASE WHEN hasRoute THEN 1 ELSE 0 END) AS withRoute,
       sum(CASE WHEN hasOrg THEN 1 ELSE 0 END) AS withOrg;
```
╒═════════╤═════════╤═══════╕
│shipments│withRoute│withOrg│
╞═════════╪═════════╪═══════╡
│20       │20       │20     │
└─────────┴─────────┴───────┘

- Facility geospatial fields present
```cypher
MATCH (f:Facility {org_id:$org})
RETURN count(*) AS facilities,
       sum(CASE WHEN f.latitude IS NOT NULL AND f.longitude IS NOT NULL THEN 1 ELSE 0 END) AS withLatLon,
       sum(CASE WHEN f.location IS NOT NULL THEN 1 ELSE 0 END) AS withPoint;
```
╒══════════╤══════════╤═════════╕
│facilities│withLatLon│withPoint│
╞══════════╪══════════╪═════════╡
│14        │14        │14       │
└──────────┴──────────┴─────────┘

- EOReading id well-formed (`facility_id::YYYY-MM`)
```cypher
MATCH (e:EOReading {org_id:$org})
WITH e, split(e.id,'::') AS parts
RETURN count(*) AS eoRows,
       sum(CASE WHEN size(parts)=2 THEN 1 ELSE 0 END) AS wellFormedId;
```
╒══════╤════════════╕
│eoRows│wellFormedId│
╞══════╪════════════╡
│98    │98          │
└──────┴────────────┘

- Orphans: routes referencing missing facilities
```cypher
MATCH (rt:Route {org_id:$org})
OPTIONAL MATCH (o:Facility {org_id:$org})-[:ORIGIN]->(rt)
OPTIONAL MATCH (rt)-[:DESTINATION]->(d:Facility {org_id:$org})
WITH rt, o IS NOT NULL AS hasO, d IS NOT NULL AS hasD
WHERE NOT (hasO AND hasD)
RETURN rt.id AS routeId, hasO, hasD
ORDER BY routeId
LIMIT 25;
```
(no changes, no records)

- Orphans: EOReading referencing missing facility
```cypher
MATCH (e:EOReading {org_id:$org})
OPTIONAL MATCH (f:Facility {id:e.facility_id, org_id:$org})
WHERE f IS NULL
RETURN e.id AS eoId, e.facility_id AS missingFacility
LIMIT 25;
```
╒═══════════════╤═══════════════╕
│eoId           │missingFacility│
╞═══════════════╪═══════════════╡
│"F001::2025-04"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-05"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-06"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-07"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-08"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-09"│"F001"         │
├───────────────┼───────────────┤
│"F001::2025-10"│"F001"         │
├───────────────┼───────────────┤
│"F002::2025-04"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-05"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-06"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-07"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-08"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-09"│"F002"         │
├───────────────┼───────────────┤
│"F002::2025-10"│"F002"         │
├───────────────┼───────────────┤
│"F003::2025-04"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-05"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-06"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-07"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-08"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-09"│"F003"         │
├───────────────┼───────────────┤
│"F003::2025-10"│"F003"         │
├───────────────┼───────────────┤
│"F004::2025-04"│"F004"         │
├───────────────┼───────────────┤
│"F004::2025-05"│"F004"         │
├───────────────┼───────────────┤
│"F004::2025-06"│"F004"         │
├───────────────┼───────────────┤
│"F004::2025-07"│"F004"         │
└───────────────┴───────────────┘

## 3) Prepare IDs for GDS

- Pick facility internal node ids (for path queries)
```cypher
MATCH (f:Facility {org_id:$org})
RETURN f.id AS facilityId, id(f) AS nodeId
ORDER BY facilityId
LIMIT 5;
```
══════════╤══════╕
│facilityId│nodeId│
╞══════════╪══════╡
│"F001"    │11    │
├──────────┼──────┤
│"F002"    │12    │
├──────────┼──────┤
│"F003"    │13    │
├──────────┼──────┤
│"F004"    │14    │
├──────────┼──────┤
│"F005"    │19    │
└──────────┴──────┘

## 4) Create in-memory graphs (required before GDS analytics)

- Facility graph creation (Facilities as nodes; edge o→d; weights from Route)
```cypher
CALL gds.graph.drop('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false);

MATCH (o:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
      -[:ORIGIN]->(rt:Route {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
      -[:DESTINATION]->(d:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
RETURN gds.graph.project(
  'org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866',
  o, d,
  { relationshipProperties: {
      distance: coalesce(rt.distance_km, 0.0),
      duration: coalesce(rt.duration_hours, 0.0),
      emission: coalesce(rt.emission_weight, coalesce(rt.distance_km, 0.0))
  } }
) AS g;
```

- Route→route graph creation (Routes as nodes; edges when routes share a facility)
```cypher
CALL gds.graph.drop('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false);

MATCH (r1:Route {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
MATCH (r2:Route {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
WHERE r1.id < r2.id
AND (
  EXISTS {
    MATCH (r1)-[:DESTINATION]->(f:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})<-[:DESTINATION]-(r2)
  } OR EXISTS {
    MATCH (r1)-[:ORIGIN]->(f:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})<-[:ORIGIN]-(r2)
  } OR EXISTS {
    MATCH (r1)-[:DESTINATION]->(f:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})<-[:ORIGIN]-(r2)
  } OR EXISTS {
    MATCH (r1)-[:ORIGIN]->(f:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})<-[:DESTINATION]-(r2)
  }
)
RETURN gds.graph.project(
  'org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866',
  r1, r2, {}
) AS g;
```

- Verify graphs
```cypher
CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount ORDER BY graphName;
```
╒═════════════════════════════════════════════════════════╤═════════╤═════════════════╕
│graphName                                                │nodeCount│relationshipCount│
╞═════════════════════════════════════════════════════════╪═════════╪═════════════════╡
│"org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866"│14       │21               │
├─────────────────────────────────────────────────────────┼─────────┼─────────────────┤
│"org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866"   │20       │30               │
└─────────────────────────────────────────────────────────┴─────────┴─────────────────┘


## 4) Facility Graph (GDS)

- Project facilities with route weights
```cypher
// Facilities with route weights (org-scoped) - pure Cypher preview
MATCH (o:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
      -[:ORIGIN]->(r:Route {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
      -[:DESTINATION]->(d:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
RETURN o.id AS originId,
       d.id AS destId,
       coalesce(r.distance_km, 0.0)      AS distance_km,
       coalesce(r.duration_hours, 0.0)   AS duration_hours,
       coalesce(r.emission_weight, coalesce(r.distance_km, 0.0)) AS emission_weight
ORDER BY originId, destId
LIMIT 200;
```
════════╤══════╤═══════════╤══════════════╤═══════════════╕
│originId│destId│distance_km│duration_hours│emission_weight│
╞════════╪══════╪═══════════╪══════════════╪═══════════════╡
│"F001"  │"F002"│1407.0     │18.0          │1407.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F001"  │"F003"│850.0      │12.0          │850.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F001"  │"F004"│1330.0     │35.0          │1330.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F001"  │"F004"│1330.0     │35.0          │1330.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F002"  │"F001"│1407.0     │14.0          │1407.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F002"  │"F004"│1740.0     │22.0          │1740.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F002"  │"F007"│2050.0     │48.0          │2050.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F003"  │"F002"│1740.0     │3.0           │1740.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F003"  │"F002"│1740.0     │28.0          │1740.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F003"  │"F005"│840.0      │14.0          │840.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F005"  │"F001"│150.0      │3.5           │150.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F006"  │"F002"│275.0      │6.0           │275.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F007"  │"F002"│2050.0     │30.0          │2050.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F101"  │"F001"│120.0      │3.0           │120.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F102"  │"F004"│1330.0     │35.0          │1330.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F103"  │"F001"│1407.0     │14.0          │1407.0         │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F103"  │"F002"│65.0       │1.5           │65.0           │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F104"  │"F003"│180.0      │4.0           │180.0          │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F107"  │"F005"│40.0       │1.0           │40.0           │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F108"  │"F006"│25.0       │0.8           │25.0           │
├────────┼──────┼───────────┼──────────────┼───────────────┤
│"F109"  │"F007"│30.0       │1.0           │30.0           │
└────────┴──────┴───────────┴──────────────┴───────────────┘

- Degree leaderboard (plain Cypher, quick)
```cypher
MATCH (f:Facility {org_id:$org})
OPTIONAL MATCH (f)-[:ORIGIN]->(:Route {org_id:$org})-[:DESTINATION]->(d:Facility {org_id:$org})
WITH f, count(d) AS outDeg
OPTIONAL MATCH (o:Facility {org_id:$org})-[:ORIGIN]->(:Route {org_id:$org})-[:DESTINATION]->(f)
WITH f, outDeg, count(o) AS inDeg
RETURN f.id AS facilityId, inDeg, outDeg, (inDeg+outDeg) AS deg
ORDER BY deg DESC, facilityId
LIMIT 15;
```
══════════╤═════╤══════╤═══╕
│facilityId│inDeg│outDeg│deg│
╞══════════╪═════╪══════╪═══╡
│"F002"    │6    │3     │9  │
├──────────┼─────┼──────┼───┤
│"F001"    │4    │4     │8  │
├──────────┼─────┼──────┼───┤
│"F003"    │2    │3     │5  │
├──────────┼─────┼──────┼───┤
│"F004"    │4    │0     │4  │
├──────────┼─────┼──────┼───┤
│"F005"    │2    │1     │3  │
├──────────┼─────┼──────┼───┤
│"F007"    │2    │1     │3  │
├──────────┼─────┼──────┼───┤
│"F006"    │1    │1     │2  │
├──────────┼─────┼──────┼───┤
│"F103"    │0    │2     │2  │
├──────────┼─────┼──────┼───┤
│"F101"    │0    │1     │1  │
├──────────┼─────┼──────┼───┤
│"F102"    │0    │1     │1  │
├──────────┼─────┼──────┼───┤
│"F104"    │0    │1     │1  │
├──────────┼─────┼──────┼───┤
│"F107"    │0    │1     │1  │
├──────────┼─────┼──────┼───┤
│"F108"    │0    │1     │1  │
├──────────┼─────┼──────┼───┤
│"F109"    │0    │1     │1  │
└──────────┴─────┴──────┴───┘


CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount RETURN graphName, nodeCount, relationshipCount ORDER BY graphName;


╒═════════════════════════════════════════════════════════╤═════════╤═════════════════╕
│graphName                                                │nodeCount│relationshipCount│
╞═════════════════════════════════════════════════════════╪═════════╪═════════════════╡
│"org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866"│14       │21               │
├─────────────────────────────────────────────────────────┼─────────┼─────────────────┤
│"org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866"   │20       │30               │
└─────────────────────────────────────────────────────────┴─────────┴─────────────────┘

- Betweenness
```cypher
//Facility 
CALL gds.betweenness.stream('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS facilityId, score
ORDER BY score DESC
LIMIT 15;

╒══════════╤══════════════════╕
│facilityId│score             │
╞══════════╪══════════════════╡
│"F002"    │28.666666666666664│
├──────────┼──────────────────┤
│"F001"    │25.666666666666668│
├──────────┼──────────────────┤
│"F003"    │13.0              │
├──────────┼──────────────────┤
│"F006"    │6.0               │
├──────────┼──────────────────┤
│"F005"    │5.666666666666667 │
├──────────┼──────────────────┤
│"F007"    │5.0               │
├──────────┼──────────────────┤
│"F004"    │0.0               │
├──────────┼──────────────────┤
│"F101"    │0.0               │
├──────────┼──────────────────┤
│"F102"    │0.0               │
├──────────┼──────────────────┤
│"F103"    │0.0               │
├──────────┼──────────────────┤
│"F104"    │0.0               │
├──────────┼──────────────────┤
│"F107"    │0.0               │
├──────────┼──────────────────┤
│"F108"    │0.0               │
├──────────┼──────────────────┤
│"F109"    │0.0               │
└──────────┴──────────────────┘

```cypher
// Route betweenness (routes graph)
CALL gds.betweenness.stream('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS routeId, score
ORDER BY score DESC
LIMIT 15;
```
╒═══════╤═════╕
│routeId│score│
╞═══════╪═════╡
│"R004" │0.0  │
├───────┼─────┤
│"R005" │0.0  │
├───────┼─────┤
│"R101" │0.0  │
├───────┼─────┤
│"R102" │0.0  │
├───────┼─────┤
│"R001" │0.0  │
├───────┼─────┤
│"R103" │0.0  │
├───────┼─────┤
│"R002" │0.0  │
├───────┼─────┤
│"R104" │0.0  │
├───────┼─────┤
│"R105" │0.0  │
├───────┼─────┤
│"R106" │0.0  │
├───────┼─────┤
│"R107" │0.0  │
├───────┼─────┤
│"R108" │0.0  │
├───────┼─────┤
│"R109" │0.0  │
├───────┼─────┤
│"R110" │0.0  │
├───────┼─────┤
│"R003" │0.0  │
└───────┴─────┘

- PageRank
```cypher
// Facility PageRank
CALL gds.pageRank.stream('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS facilityId, score
ORDER BY score DESC
LIMIT 15;
```
╒══════════╤═══════════════════╕
│facilityId│score               │
╞══════════╪═══════════════════╡
│"F002"    │1.6196440943429224 │
├──────────┼───────────────────┤
│"F004"    │1.2303053993524673 │
├──────────┼───────────────────┤
│"F001"    │1.1622843972945387 │
├──────────┼───────────────────┤
│"F007"    │0.7363646235150532 │
├──────────┼───────────────────┤
│"F003"    │0.5244703879187073 │
├──────────┼───────────────────┤
│"F005"    │0.4260931173104512 │
├──────────┼───────────────────┤
│"F006"    │0.2775             │
├──────────┼───────────────────┤
│"F101"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F102"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F103"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F104"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F107"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F108"    │0.15000000000000002│
├──────────┼───────────────────┤
│"F109"    │0.15000000000000002│
└──────────┴───────────────────┘

```cypher
// Route PageRank
CALL gds.pageRank.stream('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS routeId, score
ORDER BY score DESC
LIMIT 15;
```
╒══════════════════════════════════════╤═══════════════════╕
│routeId                               │score              │
╞══════════════════════════════════════╪═══════════════════╡
│"R115"                                │0.7199211550781252 │
├──────────────────────────────────────┼───────────────────┤
│"R106"                                │0.507478125        │
├──────────────────────────────────────┼───────────────────┤
│"d2062483-df15-4606-8986-376347f04d6f"│0.507478125        │
├──────────────────────────────────────┼───────────────────┤
│"R109"                                │0.3891465703125    │
├──────────────────────────────────────┼───────────────────┤
│"R114"                                │0.2775             │
├──────────────────────────────────────┼───────────────────┤
│"R104"                                │0.2775             │
├──────────────────────────────────────┼───────────────────┤
│"R113"                                │0.2775             │
├──────────────────────────────────────┼───────────────────┤
│"R107"                                │0.2743125          │
├──────────────────────────────────────┼───────────────────┤
│"R102"                                │0.2743125          │
├──────────────────────────────────────┼───────────────────┤
│"R108"                                │0.27308531250000007│
├──────────────────────────────────────┼───────────────────┤
│"R105"                                │0.21279375000000003│
├──────────────────────────────────────┼───────────────────┤
│"R101"                                │0.19250000000000003│
├──────────────────────────────────────┼───────────────────┤
│"R004"                                │0.19250000000000003│
├──────────────────────────────────────┼───────────────────┤
│"R103"                                │0.17550000000000002│
├──────────────────────────────────────┼───────────────────┤
│"R110"                                │0.15000000000000002│
└──────────────────────────────────────┴───────────────────┘


- Shortest path by weight (example: F001 (11) → F003 (13) by distance)
```cypher
CALL gds.shortestPath.dijkstra.stream(
  'org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866',
  { sourceNode: 11, targetNode: 13, relationshipWeightProperty: 'distance' }
)
YIELD totalCost, nodeIds
RETURN 'distance' AS weightKey,
       totalCost,
       [n IN nodeIds | gds.util.asNode(n).id] AS facilityIds;
```
╒══════════╤═════════╤════════════════╕
│weightKey │totalCost│facilityIds     │
╞══════════╪═════════╪════════════════╡
│"distance"│850.0    │["F001", "F003"]│
└──────────┴─────────┴────────────────┘

- Communities (Louvain)
```cypher
// Facility Louvain
CALL gds.louvain.stream('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).id AS facilityId, communityId
ORDER BY communityId, facilityId
LIMIT 100;
```
╒══════════╤═══════════╕
│facilityId│communityId│
╞══════════╪═══════════╡
│"F003"    │0          │
├──────────┼───────────┤
│"F104"    │0          │
├──────────┼───────────┤
│"F107"    │0          │
├──────────┼───────────┤
│"F001"    │3          │
├──────────┼───────────┤
│"F002"    │3          │
├──────────┼───────────┤
│"F004"    │3          │
├──────────┼───────────┤
│"F005"    │3          │
├──────────┼───────────┤
│"F006"    │3          │
├──────────┼───────────┤
│"F007"    │3          │
├──────────┼───────────┤
│"F101"    │3          │
├──────────┼───────────┤
│"F102"    │3          │
├──────────┼───────────┤
│"F103"    │3          │
├──────────┼───────────┤
│"F108"    │3          │
├──────────┼───────────┤
│"F109"    │3          │
└──────────┴───────────┘

```cypher
// Route Louvain
CALL gds.louvain.stream('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).id AS routeId, communityId
ORDER BY communityId, routeId
LIMIT 100;
```
╒══════════════════════════════════════╤═══════════╕
│routeId                               │communityId│
╞══════════════════════════════════════╪═══════════╡
│"R002"                                │8          │
├──────────────────────────────────────┼───────────┤
│"R104"                                │8          │
├──────────────────────────────────────┼───────────┤
│"R003"                                │10         │
├──────────────────────────────────────┼───────────┤
│"R004"                                │10         │
├──────────────────────────────────────┼───────────┤
│"R102"                                │10         │
├──────────────────────────────────────┼───────────┤
│"R106"                                │10         │
├──────────────────────────────────────┼───────────┤
│"R110"                                │15         │
├──────────────────────────────────────┼───────────┤
│"R113"                                │15         │
├──────────────────────────────────────┼───────────┤
│"R112"                                │17         │
├──────────────────────────────────────┼───────────┤
│"R114"                                │17         │
├──────────────────────────────────────┼───────────┤
│"R001"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R103"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R105"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R108"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R109"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R115"                                │18         │
├──────────────────────────────────────┼───────────┤
│"R005"                                │19         │
├──────────────────────────────────────┼───────────┤
│"R101"                                │19         │
├──────────────────────────────────────┼───────────┤
│"R107"                                │19         │
├──────────────────────────────────────┼───────────┤
│"d2062483-df15-4606-8986-376347f04d6f"│19         │
└──────────────────────────────────────┴───────────┘


## 6) EO Overlay (latest per facility)
```cypher
// EO overlay (latest per facility) for your org
MATCH (f:Facility {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
OPTIONAL MATCH (f)-[:HAS_EO_READING]->(e:EOReading {org_id:"ecfc141e-2e55-4670-bb8e-9e8813b02866"})
WITH f, e
ORDER BY f.id, e.observed_at DESC
WITH f, collect(e)[0] AS last
RETURN f.id AS facilityId, last.observed_at AS observed_at, last.aqi_score AS aqi
ORDER BY (aqi IS NULL) ASC, aqi DESC
LIMIT 20;
```
╒══════════╤════════════╤═════╕
│facilityId│observed_at │aqi  │
╞══════════╪════════════╪═════╡
│"F109"    │"2025-10-01"│124.8│
├──────────┼────────────┼─────┤
│"F102"    │"2025-10-01"│116.6│
├──────────┼────────────┼─────┤
│"F002"    │"2025-10-01"│110.2│
├──────────┼────────────┼─────┤
│"F003"    │"2025-10-01"│108.0│
├──────────┼────────────┼─────┤
│"F005"    │"2025-10-01"│106.3│
├──────────┼────────────┼─────┤
│"F001"    │"2025-10-01"│103.3│
├──────────┼────────────┼─────┤
│"F101"    │"2025-10-01"│101.7│
├──────────┼────────────┼─────┤
│"F103"    │"2025-10-01"│84.2 │
├──────────┼────────────┼─────┤
│"F107"    │"2025-10-01"│83.6 │
├──────────┼────────────┼─────┤
│"F006"    │"2025-10-01"│82.2 │
├──────────┼────────────┼─────┤
│"F104"    │"2025-10-01"│80.4 │
├──────────┼────────────┼─────┤
│"F004"    │"2025-10-01"│78.1 │
├──────────┼────────────┼─────┤
│"F007"    │"2025-10-01"│64.7 │
├──────────┼────────────┼─────┤
│"F108"    │"2025-10-01"│63.5 │
└──────────┴────────────┴─────┘

## 7) Maintenance
```cypher
// Maintenance: drop graphs for your org
CALL gds.graph.drop('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false);
CALL gds.graph.drop('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false);

SHOW INDEXES YIELD name, entityType, labelsOrTypes, properties, state
RETURN name, entityType, labelsOrTypes, properties, state ORDER BY name;
```


CALL gds.graph.drop('org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false)
CALL gds.graph.drop('org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866', false)
SHOW INDEXES YIELD name, entityType, labelsOrTypes, properties, state RETURN name, entityType, labelsOrTypes, properties, state ORDER BY name
Completed after 47 ms.