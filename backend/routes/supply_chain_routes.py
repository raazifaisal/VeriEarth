from fastapi import APIRouter, Depends, Query, HTTPException, Request
import logging, traceback
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from db.models import Facility, Route, Shipment, FacilityEnvironmentalData
from db.neo4j_service import Neo4jService
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from typing import Optional
from pydantic import BaseModel
from auth.auth import get_current_user_from_cookies, verify_password
from db.models import User

router = APIRouter(prefix="/supply-chain")

@router.get("/test-eo")
def test_eo_connection():
    """Test Google Earth Engine connection"""
    try:
        from aqi.gee_service import initialize_earth_engine
        initialize_earth_engine()
        return {"status": "success", "message": "Google Earth Engine connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Google Earth Engine connection failed: {str(e)}"}


@router.get("/test-eo-data")
def test_eo_data_fetch():
    """Test fetching actual EO data for Mumbai facility"""
    try:
        from aqi.gee_service import fetch_pollutant_data
        from datetime import datetime, timedelta
        
        # Mumbai coordinates (from our facility)
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [72.8327, 19.031],  # ~5km buffer around Mumbai facility
                [72.9227, 19.031],
                [72.9227, 19.121],
                [72.8327, 19.121],
                [72.8327, 19.031]
            ]]
        }
        
        # Last 3 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        data = fetch_pollutant_data(
            aoi=aoi,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="month"
        )
        
        return {
            "status": "success", 
            "message": f"Fetched {len(data)} EO data records",
            "sample_data": data[:3]  # First 3 records
        }
    except Exception as e:
        return {"status": "error", "message": f"EO data fetch failed: {str(e)}"}


@router.post("/organizations/{org_id}/enrich-all")
def enrich_organization_data(
    org_id: str,
    db: Session = Depends(get_db)
):
    """Complete data enrichment pipeline: EO data + Neo4j graph building"""
    from services.background_eo_service import BackgroundEOService
    from db.neo4j_service import Neo4jService
    from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    
    # Step 1: Enrich all facilities with EO data
    eo_service = BackgroundEOService(db)
    eo_results = eo_service.enrich_organization_facilities(org_id, batch_size=10)
    
    # Step 2: Build Neo4j graph from PostgreSQL data
    neo4j = Neo4jService(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
    
    try:
        # Get all facilities for the organization
        facilities = db.query(Facility).filter(Facility.organization_id == org_id).all()
        
        # Create facility nodes in Neo4j
        facility_count = 0
        for facility in facilities:
            # Get coordinates using PostGIS ST_X and ST_Y functions
            if facility.location:
                from sqlalchemy import text
                result = db.execute(
                    text("SELECT ST_X(location) as lon, ST_Y(location) as lat FROM facilities WHERE id = :id"),
                    {"id": facility.id}
                ).first()
                latitude = float(result.lat) if result else 0
                longitude = float(result.lon) if result else 0
            else:
                latitude, longitude = 0, 0
            
            neo4j.create_facility_node({
                'id': facility.id,
                'name': facility.name,
                'type': facility.facility_type,
                'latitude': latitude,
                'longitude': longitude,
                'city': facility.city,
                'country': facility.country,
                'capacity_tons': facility.capacity_tons,
            }, org_id)
            facility_count += 1
        
        # Get all routes for the organization
        routes = db.query(Route).join(Facility, Route.origin_facility_id == Facility.id).filter(
            Facility.organization_id == org_id
        ).all()
        
        # Create route relationships in Neo4j
        route_count = 0
        for route in routes:
            neo4j.create_route_relationship({
                'origin_id': route.origin_facility_id,
                'dest_id': route.destination_facility_id,
                'route_id': route.id,
                'transport_mode': route.transport_mode,
                'distance_km': route.distance_km,
                'duration_hours': route.duration_hours,
                'emission_factor': None,
            }, org_id)
            route_count += 1
        
        return {
            "status": "completed",
            "eo_enrichment": eo_results,
            "neo4j_graph": {
                "facilities_created": facility_count,
                "routes_created": route_count,
                "organization_id": org_id
            }
        }
    
    finally:
        neo4j.close()


# Synthetic EO backfill for demo
@router.post("/organizations/{org_id}/eo/backfill")
def backfill_eo_synthetic(
    org_id: str,
    db: Session = Depends(get_db)
):
    """Generate synthetic monthly EO data per facility (6 months before first record to latest)."""
    try:
        from services.eo_backfill import backfill_all_facilities
        logging.info(f"[EO_BACKFILL] start org_id={org_id}")
        summary = backfill_all_facilities(db, org_id, months_before=6)
        logging.info(f"[EO_BACKFILL] done org_id={org_id} -> {summary}")
        return {"status": "ok", **summary}
    except Exception as e:
        logging.error(f"[EO_BACKFILL] failed org_id={org_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"EO backfill failed: {e}")


class ClearEOBody(BaseModel):
    password: str


@router.post("/organizations/{org_id}/eo/clear")
def clear_eo_timeseries(
    org_id: str,
    body: ClearEOBody,
    request: Request,
    db: Session = Depends(get_db),
):
    """Master clear EO timeseries for an organization. Requires organization sudo password if set.
    Falls back to demo passwords (veriearth/confirm) if sudo not configured.
    """
    from db.models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    pwd = (body.password or "").strip()
    if org.sudo_password_hash:
        if not verify_password(pwd, org.sudo_password_hash):
            raise HTTPException(status_code=403, detail="Invalid password")
    else:
        if pwd.lower() not in {"veriearth", "confirm"}:
            raise HTTPException(status_code=403, detail="Invalid password")

    try:
        res = db.execute(text(
            "DELETE FROM facility_eo_timeseries WHERE organization_id=:org"
        ), {"org": org_id})
        db.commit()
        deleted = res.rowcount or 0
        logging.warning(f"[EO_CLEAR] org={org_id} deleted_rows={deleted}")
        return {"status": "ok", "deleted": int(deleted)}
    except Exception as e:
        db.rollback()
        logging.error(f"[EO_CLEAR] failed org_id={org_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"EO clear failed: {e}")


@router.get("/facilities/{facility_id}/eo")
def get_facility_eo_timeseries(
    facility_id: str,
    org_id: str = Query(..., description="Organization ID"),
    date_from: Optional[str] = Query(None, description="Start ISO date (inclusive)"),
    date_to: Optional[str] = Query(None, description="End ISO date (inclusive)"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return EO monthly timeseries for a facility from Postgres.
    Data source: facility_eo_timeseries (non-Timescale for now).
    """
    sql = """
        SELECT observed_at,
               aqi_score::float AS aqi_score,
               no2::float AS no2,
               co::float AS co,
               so2::float AS so2,
               o3::float AS o3,
               ch4::float AS ch4,
               aod::float AS aod,
               source,
               window_km::float AS window_km
        FROM facility_eo_timeseries
        WHERE organization_id = :org_id AND facility_id = :facility_id
          AND (:date_from IS NULL OR observed_at >= :date_from)
          AND (:date_to   IS NULL OR observed_at <= :date_to)
        ORDER BY observed_at ASC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(sql), {
        "org_id": org_id,
        "facility_id": facility_id,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
        "offset": offset,
    }).mappings().all()

    return [
        {
            "observed_at": r["observed_at"].isoformat() if r["observed_at"] else None,
            "aqi_score": r["aqi_score"],
            "no2": r["no2"],
            "co": r["co"],
            "so2": r["so2"],
            "o3": r["o3"],
            "ch4": r["ch4"],
            "aod": r["aod"],
            "source": r["source"],
            "window_km": r["window_km"],
        }
        for r in rows
    ]

@router.get("/organizations/{org_id}/eo/series")
def get_org_eo_series(
    org_id: str,
    facility_id: Optional[str] = Query(None, description="Filter by facility id"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    order: str = Query("asc", pattern="^(?i)(asc|desc)$"),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Return raw EO rows for an org with optional filters and pagination."""
    order_sql = "ASC" if order.lower() == "asc" else "DESC"
    base = f"""
        SELECT facility_id,
               observed_at,
               aqi_score::float AS aqi_score,
               no2::float AS no2,
               co::float AS co,
               so2::float AS so2,
               o3::float AS o3,
               ch4::float AS ch4,
               aod::float AS aod,
               source,
               window_km::float AS window_km
        FROM facility_eo_timeseries
        WHERE organization_id = :org
          AND (:fid IS NULL OR facility_id = :fid)
          AND (:date_from IS NULL OR observed_at >= :date_from)
          AND (:date_to   IS NULL OR observed_at <= :date_to)
        ORDER BY observed_at {order_sql}
        LIMIT :limit OFFSET :offset
    """
    sql = text(base.replace("{order_sql}", order_sql))
    rows = db.execute(sql, {
        "org": org_id,
        "fid": facility_id,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
        "offset": offset,
    }).mappings().all()

    return [
        {
            "facility_id": r["facility_id"],
            "observed_at": r["observed_at"].isoformat() if r["observed_at"] else None,
            "aqi_score": r["aqi_score"],
            "no2": r["no2"],
            "co": r["co"],
            "so2": r["so2"],
            "o3": r["o3"],
            "ch4": r["ch4"],
            "aod": r["aod"],
            "source": r["source"],
            "window_km": r["window_km"],
        }
        for r in rows
    ]

@router.get("/organizations/{org_id}/eo/available")
def get_eo_availability(
    org_id: str,
    db: Session = Depends(get_db)
):
    """Summarize EO availability per facility: count and date range."""
    sql = """
        SELECT facility_id,
               COUNT(*) AS rows,
               MIN(observed_at) AS min_ts,
               MAX(observed_at) AS max_ts
        FROM facility_eo_timeseries
        WHERE organization_id = :org
        GROUP BY facility_id
        ORDER BY facility_id
    """
    rows = db.execute(text(sql), {"org": org_id}).mappings().all()
    return [
        {
            "facility_id": r["facility_id"],
            "rows": int(r["rows"] or 0),
            "min_ts": r["min_ts"].isoformat() if r["min_ts"] else None,
            "max_ts": r["max_ts"].isoformat() if r["max_ts"] else None,
        }
        for r in rows
    ]

@router.get("/facilities")
def get_facilities(
    org_id: str = Query(..., description="Organization ID"),
    include_eo_data: bool = Query(False, description="Include latest EO data"),
    db: Session = Depends(get_db)
):
    """List all facilities for organization with optional EO enrichment"""
    facilities = db.query(Facility).filter(Facility.organization_id == org_id).all()
    
    if include_eo_data:
        # Join with latest environmental data
        for facility in facilities:
            latest_eo = db.query(FacilityEnvironmentalData).filter(
                FacilityEnvironmentalData.facility_id == facility.id
            ).order_by(FacilityEnvironmentalData.captured_at.desc()).first()
            
            facility.latest_eo_data = latest_eo
    
    return facilities

@router.post("/facilities/{facility_id}/enrich-eo")
def enrich_facility_with_eo(
    facility_id: str,
    org_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Manually trigger EO data enrichment for a specific facility"""
    from ingestion.transformers import enrich_facility_with_eo_data
    from datetime import datetime
    
    # Get facility data
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found.")
    
    # Get coordinates using PostGIS functions
    if facility.location:
        from sqlalchemy import text
        result = db.execute(
            text("SELECT ST_X(location) as lon, ST_Y(location) as lat FROM facilities WHERE id = :id"),
            {"id": facility.id}
        ).first()
        latitude = float(result.lat) if result else 0
        longitude = float(result.lon) if result else 0
    else:
        latitude, longitude = 0, 0
    
    # Prepare facility row for enrichment
    facility_row = {
        "name": facility.name,
        "latitude": latitude,
        "longitude": longitude
    }
    
    # Enrich with EO data
    enriched_row = enrich_facility_with_eo_data(facility_row)
    if enriched_row.get("eo_data"):
        eo_data = enriched_row["eo_data"]
        # Store EO data in PostgreSQL
        eo_record = FacilityEnvironmentalData(
            facility_id=facility.id,
            organization_id=org_id,
            captured_at=datetime.now(),
            no2_value=eo_data.get("no2_avg"),
            co_value=eo_data.get("co_avg"),
            hcho_value=eo_data.get("hcho_avg"),
            ch4_value=eo_data.get("ch4_avg"),
            so2_value=eo_data.get("so2_avg"),
            aod_value=eo_data.get("aod_avg"),
            o3_value=eo_data.get("o3_avg"),
            aqi_score=eo_data.get("aqi_score"),
            pollution_level=eo_data.get("pollution_level")
        )
        db.add(eo_record)
        db.commit()
        return {"status": "enriched", "facility_id": facility_id, "eo_data": eo_data}
    else:
        raise HTTPException(status_code=500, detail="Failed to enrich facility with EO data.")

@router.post("/facilities/batch-enrich")
def batch_enrich_facilities(
    org_id: str = Query(...),
    batch_size: int = Query(5, description="Number of facilities to process in parallel"),
    db: Session = Depends(get_db)
):
    """Enrich all facilities for an organization with EO data (background process)"""
    from services.background_eo_service import BackgroundEOService
    
    eo_service = BackgroundEOService(db)
    results = eo_service.enrich_organization_facilities(org_id, batch_size)
    
    return {
        "status": "completed",
        "total_facilities": results["total_facilities"],
        "enriched": results["enriched"],
        "failed": results["failed"],
        "errors": results["errors"][:10]  # Limit error messages
    }

@router.get("/facilities/enrichment-status")
def get_enrichment_status(
    org_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get EO enrichment status for an organization"""
    from services.background_eo_service import BackgroundEOService
    
    eo_service = BackgroundEOService(db)
    return eo_service.get_enrichment_status(org_id)

@router.get("/facilities/high-pollution")
def get_high_pollution_facilities(
    org_id: str = Query(...),
    threshold: float = Query(100, description="AQI threshold"),
    db: Session = Depends(get_db)
):
    """Get facilities in high-pollution areas (from PostgreSQL)"""
    from sqlalchemy import and_
    
    # Query facilities with high pollution from PostgreSQL
    high_pollution_facilities = db.query(Facility, FacilityEnvironmentalData).join(
        FacilityEnvironmentalData, Facility.id == FacilityEnvironmentalData.facility_id
    ).filter(
        and_(
            Facility.organization_id == org_id,
            FacilityEnvironmentalData.aqi_score > threshold
        )
    ).order_by(FacilityEnvironmentalData.captured_at.desc()).all()
    
    results = []
    for facility, eo_data in high_pollution_facilities:
        results.append({
            "facility_id": facility.id,
            "facility_name": facility.name,
            "aqi_score": eo_data.aqi_score,
            "pollution_level": eo_data.pollution_level,
            "captured_at": eo_data.captured_at.isoformat()
        })
    
    return results

@router.get("/routes")
def get_routes(
    org_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """List all routes for organization"""
    routes = db.query(Route).filter(Route.organization_id == org_id).all()
    return routes

@router.get("/shipments")
def get_shipments(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List shipments with optional date filtering"""
    query = db.query(Shipment).filter(Shipment.organization_id == org_id)
    
    if date_from:
        query = query.filter(Shipment.shipment_date >= date_from)
    if date_to:
        query = query.filter(Shipment.shipment_date <= date_to)
    
    return query.all()
