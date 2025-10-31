## Neo4j GDS and Cypher Query Reference (Org‑Scoped)

Notes
- All queries assume single DB (Community Edition) with tenant isolation via `org_id`.
- Replace `$ORG_ID` (and other `$params`) as needed. Use parameterized queries from the app.

### 0) Constraints and Helpful Indexes (run once)
```cypher
CREATE CONSTRAINT org_unique IF NOT EXISTS FOR (o:Organization) REQUIRE (o.id) IS UNIQUE;
CREATE CONSTRAINT facility_unique IF NOT EXISTS FOR (f:Facility) REQUIRE (f.id) IS UNIQUE;
CREATE CONSTRAINT route_unique IF NOT EXISTS FOR (r:Route) REQUIRE (r.id) IS UNIQUE;
CREATE CONSTRAINT product_unique IF NOT EXISTS FOR (p:Product) REQUIRE (p.id) IS UNIQUE;
CREATE CONSTRAINT shipment_unique IF NOT EXISTS FOR (s:Shipment) REQUIRE (s.id) IS UNIQUE;
CREATE CONSTRAINT eoreading_unique IF NOT EXISTS FOR (e:EOReading) REQUIRE (e.id) IS UNIQUE;

// Optional property indexes commonly filtered
CREATE INDEX facility_city IF NOT EXISTS FOR (f:Facility) ON (f.city);
CREATE INDEX route_mode IF NOT EXISTS FOR (r:Route) ON (r.transport_mode);
```

### 1) Facility Graph Projection (org‑scoped)
Collapse Route nodes into directed edges with weights.
```cypher
CALL gds.graph.drop('org_facility_graph_' + $org_id, false);

CALL gds.graph.project.cypher(
  'org_facility_graph_' + $org_id,
  'MATCH (f:Facility) WHERE f.org_id = $org_id RETURN id(f) AS id',
  'MATCH (o:Facility)-[:ORIGIN]->(r:Route)-[:DESTINATION]->(d:Facility)
   WHERE r.org_id = $org_id
   RETURN id(o) AS source, id(d) AS target,
          {distance: coalesce(r.distance_km,0.0),
           duration: coalesce(r.duration_hours,0.0),
           emission: coalesce(r.emission_weight, coalesce(r.distance_km,0.0))} AS properties',
  { parameters: { org_id: $org_id } }
);
```

### 2) Shortest Path (Dijkstra) by weight
```cypher
CALL gds.shortestPath.dijkstra.stream('org_facility_graph_' + $org_id, {
  sourceNode: gds.util.asNodeId($sourceFacilityNodeId),
  targetNode: gds.util.asNodeId($targetFacilityNodeId),
  relationshipWeightProperty: $weight  // 'distance' | 'duration' | 'emission'
})
YIELD totalCost, nodeIds
RETURN totalCost, [nid IN nodeIds | gds.util.asNode(nid).id] AS facilityIds;
```

Find node id from external id:
```cypher
MATCH (f:Facility {id: $facilityId, org_id: $org_id}) RETURN id(f) AS nodeId;
```

### 3) Centrality (critical facilities)
Betweenness
```cypher
CALL gds.betweenness.stream('org_facility_graph_' + $org_id)
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS facilityId, score
ORDER BY score DESC LIMIT $limit;
```

PageRank (facilities)
```cypher
CALL gds.pageRank.stream('org_facility_graph_' + $org_id)
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS facilityId, score
ORDER BY score DESC LIMIT $limit;
```

### 4) Communities (Louvain)
```cypher
CALL gds.louvain.stream('org_facility_graph_' + $org_id)
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).id AS facilityId, communityId
ORDER BY communityId, facilityId;
```

### 5) Route→Route Importance (PageRank on legs)
Project routes as nodes; edges if destination facility of r1 is origin facility of r2.
```cypher
CALL gds.graph.drop('org_route_graph_' + $org_id, false);

CALL gds.graph.project.cypher(
  'org_route_graph_' + $org_id,
  'MATCH (r:Route) WHERE r.org_id = $org_id RETURN id(r) AS id',
  'MATCH (r1:Route)-[:DESTINATION]->(:Facility)<-[:ORIGIN]-(r2:Route)
   WHERE r1.org_id = $org_id AND r2.org_id = $org_id
   RETURN id(r1) AS source, id(r2) AS target',
  { parameters: { org_id: $org_id } }
);

CALL gds.pageRank.stream('org_route_graph_' + $org_id)
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS routeId, score
ORDER BY score DESC LIMIT $limit;
```

### 6) Emission‑Weighted Edges (optional)
If you maintain per‑route emission factors, set `r.emission_weight` once.
```cypher
MATCH (r:Route {org_id: $org_id})
SET r.emission_weight = coalesce(r.distance_km,0.0) * coalesce(r.emission_factor_per_km, 1.0);
```
Then in projection, use `emission` as weight for greenest path.

### 7) Neighbors and k‑hop exploration (pure Cypher)
1‑hop neighbors for a Facility
```cypher
MATCH (f:Facility {id: $facilityId, org_id: $org_id})
OPTIONAL MATCH (f)-[:ORIGIN]->(r:Route)-[:DESTINATION]->(d:Facility)
WHERE r.org_id = $org_id
RETURN d.id AS neighborFacilityId, r.id AS viaRouteId, r.transport_mode AS mode;
```

k‑hop reachability (Facilities only)
```cypher
MATCH (s:Facility {id: $startId, org_id: $org_id})
CALL {
  WITH s MATCH p=(s)-[:ORIGIN|:DESTINATION*1..$k]-(:Facility)
  RETURN nodes(p) AS ns LIMIT 1000
}
UNWIND ns AS n WITH DISTINCT n
RETURN n.id AS facilityId LIMIT 500;
```

### 8) Cycle heuristics (small loops)
```cypher
MATCH p = (f:Facility {org_id: $org_id})-[:ORIGIN|:DESTINATION*3..6]-(f)
WITH p WHERE size(nodes(p)) = size(apoc.coll.toSet(nodes(p)))
RETURN p LIMIT 25;
```
If APOC unavailable, remove the uniqueness filter and post‑filter client‑side.

### 9) Status and counts (fast diagnostics)
Nodes/relationships by org (quick)
```cypher
CALL {
  MATCH (n:Facility {org_id: $org_id}) RETURN 'Facility' AS label, count(n) AS c
  UNION ALL
  MATCH (n:Route {org_id: $org_id}) RETURN 'Route', count(n)
  UNION ALL
  MATCH (n:Shipment {org_id: $org_id}) RETURN 'Shipment', count(n)
  UNION ALL
  MATCH (n:Supplier {org_id: $org_id}) RETURN 'Supplier', count(n)
  UNION ALL
  MATCH (n:Product {org_id: $org_id}) RETURN 'Product', count(n)
  UNION ALL
  MATCH (n:EOReading)-[:HAS_EO_READING]-(f:Facility {org_id: $org_id}) RETURN 'EOReading', count(DISTINCT n)
}
RETURN label, c ORDER BY label;
```

### 10) Maintenance
Drop projections
```cypher
CALL gds.graph.drop('org_facility_graph_' + $org_id, false);
CALL gds.graph.drop('org_route_graph_' + $org_id, false);
```

List projections
```cypher
CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount, schema
RETURN graphName, nodeCount, relationshipCount;
```

### 11) Org‑scoped greenest alternative path (end‑to‑end)
Compute emission‑weighted path and compare to distance.
```cypher
// Ensure projection exists with properties {distance, duration, emission}
WITH 'org_facility_graph_' + $org_id AS G
CALL {
  WITH G CALL gds.shortestPath.dijkstra.stream(G, {
    sourceNode: gds.util.asNodeId($srcNode),
    targetNode: gds.util.asNodeId($dstNode),
    relationshipWeightProperty: 'emission'
  }) YIELD totalCost, nodeIds
  RETURN totalCost AS emissionCost, nodeIds AS eNodes
}
CALL {
  WITH G CALL gds.shortestPath.dijkstra.stream(G, {
    sourceNode: gds.util.asNodeId($srcNode),
    targetNode: gds.util.asNodeId($dstNode),
    relationshipWeightProperty: 'distance'
  }) YIELD totalCost, nodeIds
  RETURN totalCost AS distanceCost, nodeIds AS dNodes
}
RETURN emissionCost,
       [n IN eNodes | gds.util.asNode(n).id] AS greenFacilityIds,
       distanceCost,
       [n IN dNodes | gds.util.asNode(n).id] AS shortestFacilityIds;
```

### 12) Route subgraph for a facility (routes in/out)
```cypher
MATCH (f:Facility {id: $facilityId, org_id: $org_id})
OPTIONAL MATCH (f)-[:ORIGIN]->(r1:Route)-[:DESTINATION]->(d:Facility)
OPTIONAL MATCH (o:Facility)-[:ORIGIN]->(r2:Route)-[:DESTINATION]->(f)
WHERE r1.org_id = $org_id AND r2.org_id = $org_id
RETURN DISTINCT r1.id AS outRouteId, d.id AS destFacilityId,
                r2.id AS inRouteId, o.id AS originFacilityId;
```

### 13) Emission properties from PG (if you mirror)
If you sync per‑mode emission factors from Postgres, recompute route weights in one go:
```cypher
MATCH (r:Route {org_id: $org_id})
WITH r, coalesce(r.distance_km, 0.0) AS dk, coalesce(r.factor_per_km, 1.0) AS f
SET r.emission_weight = dk * f
RETURN count(r) AS updated;
```


