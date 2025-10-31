"""
Knowledge Graph ETL API Routes
"""
import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from db.database import get_db
from services.kg_etl_service import KGETLService
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)
router = APIRouter()


def get_kg_etl(db: Session = Depends(get_db)) -> KGETLService:
    """Dependency to get KG ETL service instance"""
    return KGETLService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, db)


@router.post("/organizations/{org_id}/sync")
def sync_organization_kg(
    org_id: str,
    phase: int = Query(1, ge=1, le=3),
    last_synced_at: Optional[str] = Query(None),
    kg_etl: KGETLService = Depends(get_kg_etl),
):
    """
    Sync organization data to Neo4j knowledge graph.
    
    - Phase 1: Organization, Supplier, Facility, Route, Shipment, EOReading (monthly)
    - Phase 2: Product, PurchaseOrder (to be implemented)
    - Phase 3: Derived relationships, GDS analytics (to be implemented)
    
    Args:
        org_id: Organization UUID
        phase: ETL phase to run (1, 2, or 3)
        last_synced_at: ISO datetime string for incremental sync (optional)
    
    Returns:
        Sync statistics
    """
    try:
        last_sync = None
        if last_synced_at:
            try:
                last_sync = datetime.fromisoformat(last_synced_at.replace('Z', '+00:00'))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid last_synced_at format (use ISO 8601)")
        
        if phase == 1:
            stats = kg_etl.sync_phase1(org_id, last_sync)
            # Invalidate analytics caches after sync
            from services.redis_service import cache_delete_pattern
            cache_delete_pattern(f"gds:{org_id}:*")
            cache_delete_pattern(f"prefixspan:{org_id}:*")
            cache_delete_pattern(f"dashboard:{org_id}:*")
            cache_delete_pattern(f"eo:{org_id}:*")
            return {
                "status": "success",
                "phase": 1,
                "organization_id": org_id,
                "synced": stats,
                "message": "Phase 1 sync completed"
            }
        elif phase == 2:
            stats = kg_etl.sync_phase2(org_id, last_sync)
            # Invalidate analytics caches after sync
            from services.redis_service import cache_delete_pattern
            cache_delete_pattern(f"gds:{org_id}:*")
            cache_delete_pattern(f"prefixspan:{org_id}:*")
            cache_delete_pattern(f"dashboard:{org_id}:*")
            return {
                "status": "success",
                "phase": 2,
                "organization_id": org_id,
                "synced": stats,
                "message": "Phase 2 sync completed"
            }
        elif phase == 3:
            # TODO: implement Phase 3
            raise HTTPException(status_code=501, detail="Phase 3 not yet implemented")
        else:
            raise HTTPException(status_code=400, detail="Invalid phase (must be 1, 2, or 3)")
    
    except Exception as e:
        logger.error(f"KG sync failed for org {org_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/organizations/{org_id}/setup")
def setup_kg_constraints(
    org_id: str,
    kg_etl: KGETLService = Depends(get_kg_etl),
):
    """Setup Neo4j constraints and indexes for organization database"""
    try:
        kg_etl.setup_constraints_and_indexes(org_id)
        return {
            "status": "success",
            "message": "Constraints and indexes created (using default database with org_id isolation)"
        }
    except Exception as e:
        logger.error(f"Failed to setup constraints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.get("/organizations/{org_id}/status")
def get_kg_sync_status(
    org_id: str,
    kg_etl: KGETLService = Depends(get_kg_etl),
):
    """Get knowledge graph sync status for organization"""
    try:
        db_name = kg_etl._get_org_database_name(org_id)
        with kg_etl.neo4j_driver.session(database=db_name) as session:
            # Single parallel query using UNION ALL - much faster
            query = """
            MATCH (o:Organization {id: $org_id}) RETURN count(o) AS cnt, 'organizations' AS type
            UNION ALL
            MATCH (s:Supplier {org_id: $org_id}) RETURN count(s) AS cnt, 'suppliers' AS type
            UNION ALL
            MATCH (f:Facility {org_id: $org_id}) RETURN count(f) AS cnt, 'facilities' AS type
            UNION ALL
            MATCH (r:Route {org_id: $org_id}) RETURN count(r) AS cnt, 'routes' AS type
            UNION ALL
            MATCH (sh:Shipment {org_id: $org_id}) RETURN count(sh) AS cnt, 'shipments' AS type
            UNION ALL
            MATCH (e:EOReading {org_id: $org_id}) RETURN count(e) AS cnt, 'eo_readings' AS type
            UNION ALL
            MATCH (p:Product {org_id: $org_id}) RETURN count(p) AS cnt, 'products' AS type
            UNION ALL
            MATCH (po:PurchaseOrder {org_id: $org_id}) RETURN count(po) AS cnt, 'purchase_orders' AS type
            """
            result = session.run(query, org_id=org_id)
            
            # Build counts dict from results
            counts = {
                "organizations": 0,
                "suppliers": 0,
                "facilities": 0,
                "routes": 0,
                "shipments": 0,
                "eo_readings": 0,
                "products": 0,
                "purchase_orders": 0,
            }
            
            for record in result:
                type_name = record["type"]
                counts[type_name] = record["cnt"]
            
            return {
                "organization_id": org_id,
                "status": "synced" if counts["organizations"] > 0 else "not_synced",
                "counts": counts
            }
    except Exception as e:
        logger.error(f"Failed to get KG status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/graph")
def get_graph(
    org_id: str = Query(...),
    q: Optional[str] = Query(None, description="search in names/ids"),
    include_suppliers: bool = Query(True),
    include_facilities: bool = Query(True),
    include_routes: bool = Query(True),
    modes: Optional[str] = Query(None, description="comma list of transport_mode"),
    min_km: Optional[float] = Query(None),
    max_km: Optional[float] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    kg_etl: KGETLService = Depends(get_kg_etl),
):
    """Return a compact subgraph (nodes, edges) for filters."""
    try:
        db_name = kg_etl._get_org_database_name(org_id)
        mlist = [m.strip() for m in modes.split(',')] if modes else None
        nodes = {}
        edges = []
        with kg_etl.neo4j_driver.session(database=db_name) as session:
            if include_facilities:
                cy = [
                    "MATCH (f:Facility {org_id:$org})",
                    "WHERE ($q='' OR f.id CONTAINS $q OR f.name CONTAINS $q)",
                    "RETURN f LIMIT $limit"
                ]
                for rec in session.run("\n".join(cy), org=org_id, q=q or '', limit=limit):
                    f = rec["f"]._properties
                    nodes[f['id']] = {"id": f['id'], "type": "facility", **f}

            if include_routes:
                cy = [
                    "MATCH (o:Facility {org_id:$org})-[:ORIGIN]->(r:Route {org_id:$org})-[:DESTINATION]->(d:Facility {org_id:$org})",
                    "WHERE ($modes IS NULL OR r.transport_mode IN $modes)",
                    "  AND ($minKm IS NULL OR r.distance_km >= $minKm)",
                    "  AND ($maxKm IS NULL OR r.distance_km <= $maxKm)",
                    "  AND ($q='' OR o.id CONTAINS $q OR d.id CONTAINS $q OR o.name CONTAINS $q OR d.name CONTAINS $q)",
                    "RETURN o,r,d LIMIT $limit"
                ]
                for rec in session.run("\n".join(cy), org=org_id, modes=mlist, minKm=min_km, maxKm=max_km, q=q or '', limit=limit):
                    o = rec["o"]._properties; d = rec["d"]._properties; r = rec["r"]._properties
                    nodes[o['id']] = {"id": o['id'], "type": "facility", **o}
                    nodes[d['id']] = {"id": d['id'], "type": "facility", **d}
                    edges.append({"id": r.get('id'), "type":"route", "source": o['id'], "target": d['id'], **r})
            if include_suppliers:
                cy = [
                    "MATCH (s:Supplier {org_id:$org})-[:SUPPLIES]->(f:Facility {org_id:$org})",
                    "WHERE ($q='' OR s.name CONTAINS $q OR f.name CONTAINS $q OR s.id CONTAINS $q OR f.id CONTAINS $q)",
                    "RETURN s,f LIMIT $limit"
                ]
                for rec in session.run("\n".join(cy), org=org_id, q=q or '', limit=limit):
                    s = rec["s"]._properties; f = rec["f"]._properties
                    nodes[s['id']] = {"id": s['id'], "type": "supplier", **s}
                    nodes[f['id']] = {"id": f['id'], "type": "facility", **f}
                    edges.append({"id": f"supplies:{s['id']}->{f['id']}", "type":"supplies", "source": s['id'], "target": f['id']})
        # cut result if needed
        cut = False
        if len(edges) > limit:
            edges = edges[:limit]; cut = True
        return {"nodes": list(nodes.values()), "edges": edges, "stats": {"nodes": len(nodes), "edges": len(edges), "cut": cut}}
    except Exception as e:
        logger.error(f"Graph query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Graph fetch failed")


@router.get("/neighbors")
def get_neighbors(
    org_id: str = Query(...),
    node_id: str = Query(...),
    hops: int = Query(1, ge=1, le=2),
    kg_etl: KGETLService = Depends(get_kg_etl),
):
    """Return 1-hop neighbors for a node id (org-scoped)."""
    try:
        db_name = kg_etl._get_org_database_name(org_id)
        with kg_etl.neo4j_driver.session(database=db_name) as session:
            cy = """
            MATCH (n {org_id:$org, id:$id})-[e]-(m {org_id:$org})
            RETURN n,e,m LIMIT 500
            """
            nodes = {}
            edges = []
            for rec in session.run(cy, org=org_id, id=node_id):
                n = rec["n"]._properties; m = rec["m"]._properties; e = rec["e"].type
                nodes[n['id']] = {"id": n['id'], **n}
                nodes[m['id']] = {"id": m['id'], **m}
                edges.append({"id": f"{e}:{n['id']}->{m['id']}", "type": e.lower(), "source": n['id'], "target": m['id']})
        return {"nodes": list(nodes.values()), "edges": edges}
    except Exception as e:
        logger.error(f"Neighbors query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Neighbors fetch failed")

