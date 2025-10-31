from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from db.database import get_db
from services.kg_etl_service import KGETLService
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from sqlalchemy import text
from services.prefixspan_service import build_event_sequences, PrefixSpanMiner, score_patterns

router = APIRouter()


def get_kg_etl(db: Session = Depends(get_db)) -> KGETLService:
    return KGETLService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, db)


def _safe_name(org_id: str) -> dict:
    safe = org_id.replace('-', '_')
    return {
        "facility": f"org_facility_graph_{safe}",
        "route": f"org_route_graph_{safe}",
    }


@router.post("/graphs/build")
def build_graphs(org_id: str = Query(...), kg: KGETLService = Depends(get_kg_etl)):
    try:
        res = kg.ensure_graphs_for_org(org_id)
        return {"status": "ok", **res}
    finally:
        kg.close()


@router.get("/graphs/status")
def graphs_status(org_id: str = Query(...), kg: KGETLService = Depends(get_kg_etl)):
    try:
        dbname = kg._ensure_database_exists(org_id)
        names = _safe_name(org_id)
        with kg.neo4j_driver.session(database=dbname) as sess:
            data = sess.run("CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount RETURN graphName,nodeCount,relationshipCount").data()
        return {"graphs": data, "expected": names}
    finally:
        kg.close()


@router.delete("/graphs/clear")
def clear_graphs(org_id: str = Query(...), kg: KGETLService = Depends(get_kg_etl)):
    try:
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        with kg.neo4j_driver.session(database=dbname) as sess:
            sess.run("CALL gds.graph.drop($n, false)", {"n": names["facility"]}).consume()
            sess.run("CALL gds.graph.drop($n, false)", {"n": names["route"]}).consume()
        return {"status": "ok", "cleared": [names["facility"], names["route"]]}
    except Exception:
        # Propagate as 500 so the frontend can handle; avoid leaking internals
        raise HTTPException(status_code=500, detail="Failed to clear org graphs")
    finally:
        kg.close()


@router.get("/facilities/betweenness")
def facilities_betweenness(org_id: str = Query(...), limit: int = Query(15, ge=1, le=100), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.betweenness.stream($g) YIELD nodeId, score "
            "RETURN gds.util.asNode(nodeId).id AS facilityId, score "
            "ORDER BY score DESC LIMIT $lim"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["facility"], "lim": limit}).data()
        return rows
    finally:
        kg.close()


@router.get("/facilities/pagerank")
def facilities_pagerank(org_id: str = Query(...), limit: int = Query(15, ge=1, le=100), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.pageRank.stream($g) YIELD nodeId, score "
            "RETURN gds.util.asNode(nodeId).id AS facilityId, score "
            "ORDER BY score DESC LIMIT $lim"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["facility"], "lim": limit}).data()
        return rows
    finally:
        kg.close()


@router.get("/facilities/communities")
def facilities_communities(org_id: str = Query(...), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.louvain.stream($g) YIELD nodeId, communityId "
            "RETURN gds.util.asNode(nodeId).id AS facilityId, communityId "
            "ORDER BY communityId, facilityId"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["facility"]}).data()
        # group by community
        comm = {}
        for r in rows:
            cid = r["communityId"]
            comm.setdefault(cid, []).append(r["facilityId"])
        return [{"communityId": cid, "size": len(m), "members": m} for cid, m in comm.items()]
    finally:
        kg.close()


@router.post("/shortest-path")
def shortest_path(org_id: str, srcNode: str, dstNode: str, weight: str = Query("distance"), kg: KGETLService = Depends(get_kg_etl)):
    """Find shortest path between two facilities using facility IDs (e.g., F001, F003)."""
    if weight not in {"distance", "duration", "emission"}:
        raise HTTPException(status_code=400, detail="Invalid weight")
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        
        # Look up internal node IDs from facility IDs
        lookup_cy = (
            "MATCH (src:Facility {id: $srcId, org_id: $org}), (dst:Facility {id: $dstId, org_id: $org}) "
            "RETURN id(src) AS srcNodeId, id(dst) AS dstNodeId"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            node_ids = sess.run(lookup_cy, {"srcId": srcNode, "dstId": dstNode, "org": org_id}).single()
            if not node_ids:
                raise HTTPException(status_code=404, detail="Source or destination facility not found")
            
            cy = (
                "CALL gds.shortestPath.dijkstra.stream($g, {sourceNode:$s, targetNode:$t, relationshipWeightProperty:$w}) "
                "YIELD totalCost, nodeIds "
                "RETURN $w AS weight, totalCost, [n IN nodeIds | gds.util.asNode(n).id] AS facilityIds"
            )
            row = sess.run(cy, {"g": names["facility"], "s": node_ids["srcNodeId"], "t": node_ids["dstNodeId"], "w": weight}).single()
            if not row:
                return {"weight": weight, "totalCost": None, "facilityIds": []}
            return dict(row)
    finally:
        kg.close()


@router.get("/eo/hotspots")
def eo_hotspots(org_id: str = Query(...), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    # latest per facility + simple 3m trend (delta between latest and avg previous 2 months)
    sql = text(
        """
        WITH latest AS (
            SELECT DISTINCT ON (facility_id) facility_id, aqi_score, observed_at
            FROM facility_eo_timeseries
            WHERE organization_id = :org
            ORDER BY facility_id, observed_at DESC
        ), prev AS (
            SELECT facility_id, AVG(aqi_score) AS prev_avg
            FROM (
              SELECT facility_id, aqi_score,
                     ROW_NUMBER() OVER (PARTITION BY facility_id ORDER BY observed_at DESC) AS rn
              FROM facility_eo_timeseries
              WHERE organization_id = :org
            ) t WHERE rn BETWEEN 2 AND 3 GROUP BY facility_id
        )
        SELECT l.facility_id, l.observed_at, l.aqi_score AS aqi,
               (l.aqi_score - COALESCE(p.prev_avg, l.aqi_score)) AS trend3m
        FROM latest l
        LEFT JOIN prev p ON p.facility_id = l.facility_id
        ORDER BY aqi DESC NULLS LAST
        LIMIT :lim
        """
    )
    rows = db.execute(sql, {"org": org_id, "lim": limit}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/routes/pagerank")
def routes_pagerank(org_id: str = Query(...), limit: int = Query(15, ge=1, le=100), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.pageRank.stream($g) YIELD nodeId, score "
            "RETURN gds.util.asNode(nodeId).id AS routeId, score "
            "ORDER BY score DESC LIMIT $lim"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["route"], "lim": limit}).data()
        return rows
    finally:
        kg.close()


@router.get("/routes/betweenness")
def routes_betweenness(org_id: str = Query(...), limit: int = Query(15, ge=1, le=100), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.betweenness.stream($g) YIELD nodeId, score "
            "RETURN gds.util.asNode(nodeId).id AS routeId, score "
            "ORDER BY score DESC LIMIT $lim"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["route"], "lim": limit}).data()
        return rows
    finally:
        kg.close()


@router.get("/routes/communities")
def routes_communities(org_id: str = Query(...), kg: KGETLService = Depends(get_kg_etl)):
    try:
        kg.ensure_graphs_for_org(org_id)
        names = _safe_name(org_id)
        dbname = kg._ensure_database_exists(org_id)
        cy = (
            "CALL gds.louvain.stream($g) YIELD nodeId, communityId "
            "RETURN gds.util.asNode(nodeId).id AS routeId, communityId "
            "ORDER BY communityId, routeId"
        )
        with kg.neo4j_driver.session(database=dbname) as sess:
            rows = sess.run(cy, {"g": names["route"]}).data()
        comm = {}
        for r in rows:
            cid = r["communityId"]
            comm.setdefault(cid, []).append(r["routeId"])
        return [{"communityId": cid, "size": len(m), "members": m} for cid, m in comm.items()]
    finally:
        kg.close()


@router.post("/sequences/prefixspan")
def mine_prefixspan(
    org_id: str,
    min_support: int = Query(5, ge=1, le=10000),
    max_len: int = Query(5, ge=3, le=10),
    top_k: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    sequences, leg_weight = build_event_sequences(db, org_id, limit=5000)
    if not sequences:
        return {"patterns": [], "total_sequences": 0}
    miner = PrefixSpanMiner(sequences, min_support=min_support, max_len=max_len)
    raw = miner.mine()
    pat = score_patterns(raw, leg_weight)
    return {"patterns": pat[:top_k], "total_sequences": len(sequences)}
