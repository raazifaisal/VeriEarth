from typing import Dict, Any
from datetime import datetime, timedelta
from aqi.gee_service import fetch_pollutant_data
import logging

logger = logging.getLogger(__name__)


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]


def parse_date(value: str) -> str:
    v = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(v, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return v


def normalize_facility(row: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(row)
    if row.get("type"):
        row["type"] = str(row["type"]).strip().lower()
    return row


def normalize_route(row: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(row)
    for f in ("pickup_date", "delivery_date", "expected_delivery_date"):
        if row.get(f):
            row[f] = parse_date(str(row[f]))
    return row


def enrich_facility_with_eo_data(facility_row: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich facility data with Earth Observation data"""
    try:
        # Extract coordinates
        lat = float(facility_row.get("latitude", 0))
        lon = float(facility_row.get("longitude", 0))
        
        if lat == 0 or lon == 0:
            logger.warning(f"Facility {facility_row.get('name')} has no valid coordinates")
            return facility_row
        
        # Create AOI around facility (5km buffer)
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [lon - 0.045, lat - 0.045],  # ~5km buffer
                [lon + 0.045, lat - 0.045],
                [lon + 0.045, lat + 0.045],
                [lon - 0.045, lat + 0.045],
                [lon - 0.045, lat - 0.045]
            ]]
        }
        
        # Fetch last 3 months of EO data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        eo_data = fetch_pollutant_data(
            aoi=aoi,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="month"
        )
        
        # Calculate aggregate metrics
        enriched_data = _calculate_pollution_metrics(eo_data)
        
        # Add EO data to facility row
        facility_row["eo_data"] = enriched_data
        logger.info(f"Enriched facility {facility_row.get('name')} with EO data")
        
    except Exception as e:
        logger.error(f"Failed to enrich facility {facility_row.get('name')} with EO data: {e}")
        facility_row["eo_data"] = None
    
    return facility_row


def _calculate_pollution_metrics(eo_data: list) -> dict:
    """Calculate AQI score and pollution level from EO data"""
    if not eo_data:
        return {"aqi_score": None, "pollution_level": "unknown"}
    
    # Aggregate pollutants
    pollutants = {}
    for record in eo_data:
        pollutant = record.get("pollutant")
        value = record.get("value")
        if value is not None:
            if pollutant not in pollutants:
                pollutants[pollutant] = []
            pollutants[pollutant].append(value)
    
    # Calculate averages
    avg_pollutants = {
        p: sum(values) / len(values) 
        for p, values in pollutants.items()
    }
    
    # Simple AQI calculation (placeholder - use proper AQI formula)
    no2_avg = avg_pollutants.get("NO2", 0)
    aqi_score = min(500, no2_avg * 1e15)  # Scale factor
    
    # Determine pollution level
    if aqi_score < 50:
        level = "good"
    elif aqi_score < 100:
        level = "moderate"
    elif aqi_score < 150:
        level = "unhealthy_sensitive"
    elif aqi_score < 200:
        level = "unhealthy"
    else:
        level = "hazardous"
    
    return {
        "aqi_score": round(aqi_score, 2),
        "pollution_level": level,
        "no2_avg": round(avg_pollutants.get("NO2", 0), 6),
        "co_avg": round(avg_pollutants.get("CO", 0), 6),
        "hcho_avg": round(avg_pollutants.get("HCHO", 0), 6),
        "ch4_avg": round(avg_pollutants.get("CH4", 0), 6),
        "so2_avg": round(avg_pollutants.get("SO2", 0), 6),
        "aod_avg": round(avg_pollutants.get("AOD", 0), 6),
        "o3_avg": round(avg_pollutants.get("O3", 0), 6),
    }


