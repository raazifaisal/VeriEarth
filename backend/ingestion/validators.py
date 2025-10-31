from typing import Dict, Any, List, Tuple


def _has(values: Dict[str, Any], keys: List[str]) -> List[str]:
    return [k for k in keys if not values.get(k)]


def validate_suppliers(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = _has(row, ["supplier_id", "name", "country"])
    if missing:
        errors.append(f"missing fields: {','.join(missing)}")
    try:
        if row.get("latitude") is not None:
            lat = float(row["latitude"])  # type: ignore[arg-type]
            if lat < -90 or lat > 90:
                errors.append("latitude out of range")
        if row.get("longitude") is not None:
            lon = float(row["longitude"])  # type: ignore[arg-type]
            if lon < -180 or lon > 180:
                errors.append("longitude out of range")
    except Exception:
        errors.append("invalid latitude/longitude")
    return errors


def validate_facilities(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = _has(row, ["name", "country"])
    if missing:
        errors.append(f"missing fields: {','.join(missing)}")
    
    # Set facility_id if not provided (use name as fallback)
    if not row.get("facility_id"):
        row["facility_id"] = row.get("name", "unknown").replace(" ", "_").lower()
    
    # Type is optional - if not provided, we'll infer it from the name
    if row.get("type"):
        allowed = {"manufacturing", "warehouse", "distribution_center", "retail"}
        ftype = (row.get("type") or "").strip().lower()
        if ftype not in allowed:
            errors.append("invalid facility type")
    return errors


def validate_routes(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = _has(row, ["route_id", "origin_facility_id", "destination_facility_id"])
    if missing:
        errors.append(f"missing fields: {','.join(missing)}")
    
    # Set default transport_mode if not provided
    if not row.get("transport_mode"):
        row["transport_mode"] = "road_truck"  # Default transport mode
    
    try:
        if row.get("distance_km") is not None:
            d = float(row["distance_km"])  # type: ignore[arg-type]
            if d < 0:
                errors.append("distance_km must be >= 0")
    except Exception:
        errors.append("invalid distance_km")
    return errors


def validate_shipments(row: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = _has(row, ["shipment_id", "origin_facility_id", "destination_facility_id", "weight_kg"])
    if missing:
        errors.append(f"missing fields: {','.join(missing)}")
    
    # Set default transport_mode if not provided
    if not row.get("transport_mode"):
        row["transport_mode"] = "road_truck"  # Default transport mode
    
    try:
        w = float(row.get("weight_kg", 0) or 0)  # type: ignore[arg-type]
        if w <= 0:
            errors.append("weight_kg must be > 0")
    except Exception:
        errors.append("invalid weight_kg")
    return errors


VALIDATORS = {
    "suppliers": validate_suppliers,
    "facilities": validate_facilities,
    "routes": validate_routes,
    "shipments": validate_shipments,
}


