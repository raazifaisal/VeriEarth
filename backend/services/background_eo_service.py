"""
Background EO Enrichment Service

This service handles EO data enrichment in the background after data ingestion.
It processes facilities in batches to avoid blocking the main ingestion pipeline.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from db.models import Facility, FacilityEnvironmentalData
from ingestion.transformers import enrich_facility_with_eo_data
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


class BackgroundEOService:
    """Service for background EO data enrichment"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def enrich_facility_batch(self, facility_ids: List[str], organization_id: str, batch_size: int = 5) -> Dict[str, Any]:
        """
        Enrich a batch of facilities with EO data
        
        Args:
            facility_ids: List of facility IDs to enrich
            organization_id: Organization ID for data isolation
            batch_size: Number of facilities to process in parallel (default: 5)
        
        Returns:
            Dict with enrichment results
        """
        results = {
            "total_facilities": len(facility_ids),
            "enriched": 0,
            "failed": 0,
            "errors": []
        }
        
        # Process facilities in batches to avoid overwhelming the GEE API
        for i in range(0, len(facility_ids), batch_size):
            batch = facility_ids[i:i + batch_size]
            logger.info(f"Processing EO enrichment batch {i//batch_size + 1}: {len(batch)} facilities")
            
            for facility_id in batch:
                try:
                    success = self._enrich_single_facility(facility_id, organization_id)
                    if success:
                        results["enriched"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Facility {facility_id}: No EO data available")
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Facility {facility_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                
                # Small delay between facilities to be respectful to GEE API
                time.sleep(1)
        
        logger.info(f"EO enrichment completed: {results['enriched']} enriched, {results['failed']} failed")
        return results
    
    def _enrich_single_facility(self, facility_id: str, organization_id: str) -> bool:
        """Enrich a single facility with EO data"""
        facility = self.db.query(Facility).filter(Facility.id == facility_id).first()
        if not facility or not facility.location:
            logger.warning(f"Facility {facility_id} not found or has no location")
            return False
        
        # Get coordinates using PostGIS functions
        if facility.location:
            from sqlalchemy import text
            result = self.db.execute(
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
        if not enriched_row.get("eo_data"):
            return False
        
        eo_data = enriched_row["eo_data"]
        
        # Store EO data in PostgreSQL
        eo_record = FacilityEnvironmentalData(
            facility_id=facility.id,
            organization_id=organization_id,
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
        
        self.db.add(eo_record)
        self.db.commit()
        
        logger.info(f"Successfully enriched facility {facility.name} with EO data")
        return True
    
    def enrich_organization_facilities(self, organization_id: str, batch_size: int = 5) -> Dict[str, Any]:
        """Enrich all facilities for an organization"""
        facilities = self.db.query(Facility).filter(
            Facility.organization_id == organization_id
        ).all()
        
        facility_ids = [f.id for f in facilities]
        return self.enrich_facility_batch(facility_ids, organization_id, batch_size)
    
    def get_enrichment_status(self, organization_id: str) -> Dict[str, Any]:
        """Get EO enrichment status for an organization"""
        total_facilities = self.db.query(Facility).filter(
            Facility.organization_id == organization_id
        ).count()
        
        enriched_facilities = self.db.query(FacilityEnvironmentalData).filter(
            FacilityEnvironmentalData.organization_id == organization_id
        ).count()
        
        return {
            "total_facilities": total_facilities,
            "enriched_facilities": enriched_facilities,
            "enrichment_percentage": (enriched_facilities / total_facilities * 100) if total_facilities > 0 else 0
        }
