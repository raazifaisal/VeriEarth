from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Facility, Route, Shipment, FacilityEnvironmentalData
from db.neo4j_service import Neo4jService
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from typing import Optional

router = APIRouter(prefix="/api/supply-chain", tags=["supply-chain"])

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
    
    # Prepare facility row for enrichment
    facility_row = {
        "name": facility.name,
        "latitude": facility.location.y if facility.location else 0,
        "longitude": facility.location.x if facility.location else 0
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
