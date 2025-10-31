# Analytics Sample Responses (Org: ecfc141e-2e55-4670-bb8e-9e8813b02866)

## Build graphs (POST /api/kg/analytics/graphs/build)
```json
{"status":"ok","built":{},"graphs":[{"graphName":"org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866","nodeCount":20,"relationshipCount":30},{"graphName":"org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866","nodeCount":14,"relationshipCount":21}]}
```

## Graph status (GET /api/kg/analytics/graphs/status)
```json
{"graphs":[{"graphName":"org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866","nodeCount":20,"relationshipCount":30},{"graphName":"org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866","nodeCount":14,"relationshipCount":21}],"expected":{"facility":"org_facility_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866","route":"org_route_graph_ecfc141e_2e55_4670_bb8e_9e8813b02866"}}
```

## Facility betweenness (GET /api/kg/analytics/facilities/betweenness)
```json
[{"facilityId":"F002","score":28.666666666666664},{"facilityId":"F001","score":25.666666666666664},{"facilityId":"F003","score":13.0},{"facilityId":"F006","score":6.0},{"facilityId":"F005","score":5.666666666666667},{"facilityId":"F007","score":5.0},{"facilityId":"F103","score":0.0},{"facilityId":"F102","score":0.0},{"facilityId":"F101","score":0.0},{"facilityId":"F104","score":0.0}]
```

## Facility PageRank (GET /api/kg/analytics/facilities/pagerank)
```json
[{"facilityId":"F002","score":1.6196440943429224},{"facilityId":"F004","score":1.2303053993524673},{"facilityId":"F001","score":1.1622843972945387},{"facilityId":"F007","score":0.7363646235150532},{"facilityId":"F003","score":0.5244703879187073},{"facilityId":"F005","score":0.4260931173104512},{"facilityId":"F006","score":0.2775},{"facilityId":"F103","score":0.15000000000000002},{"facilityId":"F102","score":0.15000000000000002},{"facilityId":"F101","score":0.15000000000000002}]
```

## Facility communities (GET /api/kg/analytics/facilities/communities)
```json
[{"communityId":0,"size":3,"members":["F003","F104","F107"]},{"communityId":3,"size":11,"members":["F001","F002","F004","F005","F006","F007","F101","F102","F103","F108","F109"]}]
```

## Route PageRank (GET /api/kg/analytics/routes/pagerank)
```json
[{"routeId":"R115","score":0.7199211550781252},{"routeId":"de6546d9-f148-4931-a5c2-a924174a10ff","score":0.507478125},{"routeId":"R106","score":0.507478125},{"routeId":"R109","score":0.3891465703125},{"routeId":"R114","score":0.2775},{"routeId":"R104","score":0.2775},{"routeId":"R113","score":0.2775},{"routeId":"R107","score":0.2743125},{"routeId":"R102","score":0.2743125},{"routeId":"R108","score":0.27308531250000007}]
```

## Route betweenness (GET /api/kg/analytics/routes/betweenness)
```json
[{"routeId":"R004","score":0.0},{"routeId":"R005","score":0.0},{"routeId":"R101","score":0.0},{"routeId":"R102","score":0.0},{"routeId":"R001","score":0.0},{"routeId":"R103","score":0.0},{"routeId":"R002","score":0.0},{"routeId":"R104","score":0.0},{"routeId":"R105","score":0.0},{"routeId":"R003","score":0.0}]
```

## Route communities (GET /api/kg/analytics/routes/communities)
```json
[{"communityId":8,"size":2,"members":["R002","R104"]},{"communityId":10,"size":4,"members":["R003","R004","R102","R106"]},{"communityId":15,"size":2,"members":["R110","R113"]},{"communityId":17,"size":2,"members":["R112","R114"]},{"communityId":18,"size":6,"members":["R001","R103","R105","R108","R109","R115"]},{"communityId":19,"size":4,"members":["R005","R101","R107","de6546d9-f148-4931-a5c2-a924174a10ff"]}]
```

## Shortest path (POST /api/kg/analytics/shortest-path)
### By distance
```json
{"weight":"distance","totalCost":120.0,"facilityIds":["F101","F001"]}
```

### By emission
```json
{"weight":"emission","totalCost":220.44,"facilityIds":["F101","F001"]}
```

**Note**: 
- Uses facility IDs (e.g., F001, F101) for srcNode/dstNode
- `weight` can be `distance` (km), `duration` (hours), or `emission` (kg CO₂)
- `emission` weight = sum of `total_emissions_kg_co2` from all shipments on each route

## PrefixSpan frequent patterns (POST /api/kg/analytics/sequences/prefixspan)
```json
{
  "patterns": [
    {"pattern": ["F101","ROAD_TRUCK","F001"], "support_count": 4, "emission_sum": 220.44, "emission_avg": 220.44},
    {"pattern": ["F103","RAIL_FREIGHT","F001"], "support_count": 4, "emission_sum": 130.851, "emission_avg": 130.851},
    {"pattern": ["F102","SEA_CONTAINER","F004"], "support_count": 4, "emission_sum": 52.535, "emission_avg": 52.535},
    {"pattern": ["F104","ROAD_TRUCK","F003"], "support_count": 4, "emission_sum": 14.508, "emission_avg": 14.508},
    {"pattern": ["F103","ROAD_TRUCK","F002"], "support_count": 4, "emission_sum": 3.534, "emission_avg": 3.534}
  ],
  "total_sequences": 20
}
```

**Note**: 
- Finds frequent route patterns (origin → mode → destination) that occur often
- `emission_sum` = total kg CO₂ across all occurrences (identifies "invisible heavy hitters")
- Sorted by support_count then emission_sum (high frequency + high impact)

## EO hotspots (GET /api/kg/analytics/eo/hotspots)
```json
[{"facility_id":"F109","observed_at":"2025-10-01T00:00:00+00:00","aqi":124.8,"trend3m":16.6},{"facility_id":"F102","observed_at":"2025-10-01T00:00:00+00:00","aqi":116.6,"trend3m":36.75},{"facility_id":"F002","observed_at":"2025-10-01T00:00:00+00:00","aqi":110.2,"trend3m":17.05},{"facility_id":"F003","observed_at":"2025-10-01T00:00:00+00:00","aqi":108.0,"trend3m":38.2},{"facility_id":"F005","observed_at":"2025-10-01T00:00:00+00:00","aqi":106.3,"trend3m":-8.8},{"facility_id":"F001","observed_at":"2025-10-01T00:00:00+00:00","aqi":103.3,"trend3m":-8.75},{"facility_id":"F101","observed_at":"2025-10-01T00:00:00+00:00","aqi":101.7,"trend3m":-8.7},{"facility_id":"F103","observed_at":"2025-10-01T00:00:00+00:00","aqi":84.2,"trend3m":-12.65},{"facility_id":"F107","observed_at":"2025-10-01T00:00:00+00:00","aqi":83.6,"trend3m":-14.3},{"facility_id":"F006","observed_at":"2025-10-01T00:00:00+00:00","aqi":82.2,"trend3m":-35.9}]
```

---
Use these payloads to shape frontend cards/tables per `ANALYTICS_MVP_SPEC.md` and copy text/insight framing from `ANALYTICS_BUSINESS_SPEC.md`.
