from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from services.redis_service import make_cache_key, cache_get, cache_set

router = APIRouter(prefix="/dashboard")

# Emission factors kg CO2e per tonne·km
EMISSION_FACTORS = {
    "road_truck": 0.062,
    "rail_freight": 0.022,
    "sea_container": 0.010,
    "air_cargo": 0.602,
}

def _emissions_expr():
    # weight_tonne_km * factor per mode
    return (
        "((COALESCE(s.weight_kg,0)/1000.0) * COALESCE(r.distance_km,0)) * "
        "CASE r.transport_mode::text "
        " WHEN 'road_truck' THEN 0.062"
        " WHEN 'rail_freight' THEN 0.022"
        " WHEN 'sea_container' THEN 0.010"
        " WHEN 'air_cargo' THEN 0.602"
        " ELSE 0.062 END"
    )


@router.get("/kpis")
def get_kpis(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    facility_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "kpis", date_from=date_from, date_to=date_to, facility_id=facility_id, supplier_id=supplier_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    # If no dates provided, expand to full data range for the org; else use given
    if not date_from or not date_to:
        span = db.execute(text(
            """
            SELECT MIN(s.shipment_date) AS min_d, MAX(s.shipment_date) AS max_d
            FROM shipments s
            WHERE s.organization_id = :org
            """
        ), {"org": org_id}).mappings().first()
        if span:
            if not date_from and span["min_d"] is not None:
                date_from = span["min_d"].isoformat()
            if not date_to and span["max_d"] is not None:
                date_to = span["max_d"].isoformat()

    # Default window: last 90 days if still not provided
    # Compute previous window for trend (same length immediately before current window)
    window_sql = """
      WITH bounds AS (
        SELECT
          COALESCE(CAST(:df AS timestamptz), NOW() - INTERVAL '90 days') AS df,
          COALESCE(CAST(:dt AS timestamptz), NOW()) AS dt
      ), prev AS (
        SELECT (df - (dt - df))::timestamptz AS pdf,
               (df - INTERVAL '1 second')::timestamptz AS pdt
        FROM bounds
      )
      SELECT df, dt, pdf, pdt FROM bounds, prev
    """
    b = db.execute(text(window_sql), {"df": date_from, "dt": date_to}).mappings().first()
    df, dt, pdf, pdt = b["df"], b["dt"], b["pdf"], b["pdt"]

    filters = ["s.organization_id = :org"]
    params = {"org": org_id}
    filters.append("s.shipment_date >= :df AND s.shipment_date <= :dt")
    params.update({"df": df, "dt": dt})
    if facility_id:
        filters.append("(s.origin_facility_id = :fid OR s.destination_facility_id = :fid)")
        params["fid"] = facility_id
    if supplier_id:
        filters.append("s.supplier_id = :sid")
        params["sid"] = supplier_id
    where = " AND ".join(filters)

    sql = f"""
      WITH base AS (
        SELECT s.id,
               COALESCE(r.distance_km,0) AS distance_km,
               ((COALESCE(s.weight_kg,0)/1000.0) * COALESCE(r.distance_km,0)) AS tonne_km,
               {_emissions_expr()} AS emissions_kg
        FROM shipments s
        JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
        WHERE {where}
      ), prev AS (
        SELECT s.id,
               COALESCE(r.distance_km,0) AS distance_km,
               ((COALESCE(s.weight_kg,0)/1000.0) * COALESCE(r.distance_km,0)) AS tonne_km,
               {_emissions_expr()} AS emissions_kg
        FROM shipments s
        JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
        WHERE s.organization_id = :org
          AND s.shipment_date >= :pdf AND s.shipment_date <= :pdt
          {" AND (s.origin_facility_id = :fid OR s.destination_facility_id = :fid)" if facility_id else ''}
          {" AND s.supplier_id = :sid" if supplier_id else ''}
      )
      SELECT 
        (SELECT COUNT(*) FROM facilities f WHERE f.organization_id = :org) AS total_facilities,
        (SELECT COUNT(*) FROM base) AS total_shipments,
        (SELECT COALESCE(SUM(distance_km),0) FROM base) AS total_distance_km,
        (SELECT COALESCE(SUM(emissions_kg),0) FROM base) AS total_emissions_kg,
        (
          SELECT CASE WHEN COALESCE(SUM(tonne_km),0) = 0 THEN 0
                      ELSE COALESCE(SUM(emissions_kg),0)/NULLIF(SUM(tonne_km),0) END
          FROM base
        ) AS avg_unit_emissions,
        (
          SELECT COALESCE(AVG(aqi_score),0)
          FROM (
            SELECT DISTINCT ON (facility_id)
                   facility_id, aqi_score
            FROM facility_eo_timeseries
            WHERE organization_id = :org
            ORDER BY facility_id, observed_at DESC
          ) t
        ) AS avg_aqi_recent,
        (
          SELECT COUNT(*) FROM (
            SELECT DISTINCT r.id
            FROM routes r
            WHERE r.organization_id = :org
          ) q
        ) AS active_routes,
        -- Previous period for trends
        (SELECT COUNT(*) FROM prev) AS prev_shipments,
        (SELECT COALESCE(SUM(distance_km),0) FROM prev) AS prev_distance_km,
        (SELECT COALESCE(SUM(emissions_kg),0) FROM prev) AS prev_emissions_kg
    """
    row = db.execute(text(sql), {**params, "pdf": pdf, "pdt": pdt}).mappings().first()

    # AQI category and poor-air-quality count
    aqi_sql = """
      WITH latest AS (
        SELECT DISTINCT ON (facility_id)
               facility_id, aqi_score
        FROM facility_eo_timeseries
        WHERE organization_id = :org
        ORDER BY facility_id, observed_at DESC
      )
      SELECT aqi_score FROM latest
    """
    aqi_rows = db.execute(text(aqi_sql), {"org": org_id}).fetchall()
    aqi_vals = [float(r[0]) for r in aqi_rows if r[0] is not None]
    def cat(v: float) -> str:
        return (
            "Good" if v < 50 else
            "Moderate" if v < 100 else
            "Unhealthy" if v < 150 else
            "Very Unhealthy" if v < 200 else
            "Hazardous"
        )
    dominant_category = None
    if aqi_vals:
        from collections import Counter
        dominant_category = Counter([cat(v) for v in aqi_vals]).most_common(1)[0][0]
    poor_count = sum(1 for v in aqi_vals if v >= 150)

    resp = dict(row or {})
    resp.update({
        "trend": {
            "shipments": {
                "current": float(resp.get("total_shipments", 0) or 0),
                "previous": float(resp.get("prev_shipments", 0) or 0),
            },
            "distance_km": {
                "current": float(resp.get("total_distance_km", 0) or 0),
                "previous": float(resp.get("prev_distance_km", 0) or 0),
            },
            "emissions_kg": {
                "current": float(resp.get("total_emissions_kg", 0) or 0),
                "previous": float(resp.get("prev_emissions_kg", 0) or 0),
            },
        },
        "poor_air_quality": poor_count,
        "aqi_category": dominant_category,
    })
    # Remove prev fields from top-level
    for k in ("prev_shipments", "prev_distance_km", "prev_emissions_kg"):
        resp.pop(k, None)
    cache_set(cache_key, resp, ttl=300)  # 5 minutes
    return resp


@router.get("/emissions-trend")
def emissions_trend(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    interval: str = Query("month", pattern="^(day|week|month)$"),
    facility_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "emissions-trend", date_from=date_from, date_to=date_to, interval=interval, facility_id=facility_id, supplier_id=supplier_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    bucket = {
        "day": "DATE_TRUNC('day', s.shipment_date)",
        "week": "DATE_TRUNC('week', s.shipment_date)",
        "month": "DATE_TRUNC('month', s.shipment_date)",
    }[interval]
    filters = ["s.organization_id = :org"]
    params = {"org": org_id}
    if date_from:
        filters.append("s.shipment_date >= :df")
        params["df"] = date_from
    if date_to:
        filters.append("s.shipment_date <= :dt")
        params["dt"] = date_to
    if facility_id:
        filters.append("(s.origin_facility_id = :fid OR s.destination_facility_id = :fid)")
        params["fid"] = facility_id
    if supplier_id:
        filters.append("s.supplier_id = :sid")
        params["sid"] = supplier_id
    where = " AND ".join(filters)

    sql = f"""
      SELECT {bucket} AS period_start,
             SUM(((COALESCE(s.weight_kg,0)/1000.0) * COALESCE(r.distance_km,0))) AS tonne_km,
             SUM({_emissions_expr()}) AS emissions_kg
      FROM shipments s
      JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
      WHERE {where}
      GROUP BY 1
      ORDER BY 1
    """
    rows = db.execute(text(sql), params).mappings().all()
    result = []
    for r in rows:
        tk = float(r["tonne_km"] or 0)
        em = float(r["emissions_kg"] or 0)
        result.append({
            "period_start": r["period_start"].isoformat() if r["period_start"] else None,
            "emissions_kg": em,
            "weight_tonne_km": tk,
            "unit_emissions": (em / tk) if tk else 0.0,
        })
    cache_set(cache_key, result, ttl=900)  # 15 minutes
    return result


@router.get("/transport-distribution")
def transport_distribution(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    facility_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "transport-distribution", date_from=date_from, date_to=date_to, facility_id=facility_id, supplier_id=supplier_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    filters = ["s.organization_id = :org"]
    params = {"org": org_id}
    if date_from:
        filters.append("s.pickup_date >= :df")
        params["df"] = date_from
    if date_to:
        filters.append("s.pickup_date <= :dt")
        params["dt"] = date_to
    if facility_id:
        filters.append("(s.origin_facility_id = :fid OR s.destination_facility_id = :fid)")
        params["fid"] = facility_id
    if supplier_id:
        filters.append("s.supplier_id = :sid")
        params["sid"] = supplier_id
    where = " AND ".join(filters)

    sql = f"""
      WITH base AS (
        SELECT r.transport_mode,
               1 AS shipments,
               COALESCE(r.distance_km,0) AS distance_km,
               {_emissions_expr()} AS emissions_kg
        FROM shipments s
        JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
        WHERE {where}
      )
      SELECT transport_mode,
             COUNT(*) AS shipments,
             COALESCE(SUM(distance_km),0) AS distance_km,
             COALESCE(SUM(emissions_kg),0) AS emissions_kg
      FROM base
      GROUP BY transport_mode
    """
    rows = db.execute(text(sql), params).mappings().all()
    total_ship = sum(int(r["shipments"]) for r in rows) or 1
    total_em = sum(float(r["emissions_kg"] or 0) for r in rows) or 1.0
    result = []
    for r in rows:
        tk = None  # not returned here; can be added if needed
        em = float(r["emissions_kg"] or 0)
        result.append({
            "transport_mode": r["transport_mode"],
            "shipments": int(r["shipments"]),
            "distance_km": float(r["distance_km"] or 0),
            "emissions_kg": em,
            "unit_emissions": None,
            "share_shipments": (int(r["shipments"]) / total_ship),
            "share_emissions": (em / total_em),
        })
    cache_set(cache_key, result, ttl=600)  # 10 minutes
    return result


@router.get("/top-routes")
def top_routes(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "top-routes", date_from=date_from, date_to=date_to, limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    filters = ["s.organization_id = :org"]
    params = {"org": org_id, "limit": limit}
    if date_from:
        filters.append("s.pickup_date >= :df")
        params["df"] = date_from
    if date_to:
        filters.append("s.pickup_date <= :dt")
        params["dt"] = date_to
    where = " AND ".join(filters)

    sql = f"""
      SELECT s.origin_facility_id AS origin_id,
             s.destination_facility_id AS dest_id,
             COUNT(*) AS shipments,
             COALESCE(SUM(r.distance_km),0) AS distance_km,
             SUM({_emissions_expr()}) AS emissions_kg
      FROM shipments s
      JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
      WHERE {where}
      GROUP BY s.origin_facility_id, s.destination_facility_id
      ORDER BY emissions_kg DESC
      LIMIT :limit
    """
    rows = db.execute(text(sql), params).mappings().all()
    # Resolve facility names
    ids = set()
    for r in rows:
        if r["origin_id"]: ids.add(r["origin_id"])
        if r["dest_id"]: ids.add(r["dest_id"])
    name_map = {}
    if ids:
        name_rows = db.execute(text(
            "SELECT id, name FROM facilities WHERE id = ANY(:ids)"
        ), {"ids": list(ids)}).mappings().all()
        name_map = {nr["id"]: nr["name"] for nr in name_rows}
    result = []
    for r in rows:
        result.append({
            "origin_id": r["origin_id"],
            "origin_name": name_map.get(r["origin_id"], r["origin_id"]),
            "dest_id": r["dest_id"],
            "dest_name": name_map.get(r["dest_id"], r["dest_id"]),
            "shipments": int(r["shipments"]),
            "distance_km": float(r["distance_km"] or 0),
            "emissions_kg": float(r["emissions_kg"] or 0),
        })
    cache_set(cache_key, result, ttl=600)  # 10 minutes
    return result


@router.get("/carriers")
def carriers(
    org_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "carriers", date_from=date_from, date_to=date_to, limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    filters = ["s.organization_id = :org"]
    params = {"org": org_id, "limit": limit}
    if date_from:
        filters.append("s.pickup_date >= :df")
        params["df"] = date_from
    if date_to:
        filters.append("s.pickup_date <= :dt")
        params["dt"] = date_to
    where = " AND ".join(filters)

    sql = f"""
      SELECT COALESCE(s.carrier,'Unknown') AS carrier,
             COUNT(*) AS shipments,
             COALESCE(SUM(r.distance_km),0) AS distance_km,
             SUM({_emissions_expr()}) AS emissions_kg
      FROM shipments s
      JOIN routes r ON r.id = s.route_id AND r.organization_id = s.organization_id
      WHERE {where}
      GROUP BY COALESCE(s.carrier,'Unknown')
      ORDER BY emissions_kg DESC
      LIMIT :limit
    """
    rows = db.execute(text(sql), params).mappings().all()
    result = []
    for r in rows:
        tk = None
        em = float(r["emissions_kg"] or 0)
        result.append({
            "carrier": r["carrier"],
            "shipments": int(r["shipments"]),
            "distance_km": float(r["distance_km"] or 0),
            "emissions_kg": em,
            "unit_emissions": None,
        })
    cache_set(cache_key, result, ttl=600)  # 10 minutes
    return result


@router.get("/facilities-aqi")
def facilities_aqi(
    org_id: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key("dashboard", org_id, "facilities-aqi", limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    sql = """
      WITH latest AS (
        SELECT DISTINCT ON (facility_id)
               facility_id, observed_at, aqi_score
        FROM facility_eo_timeseries
        WHERE organization_id = :org
        ORDER BY facility_id, observed_at DESC
      ), prev AS (
        SELECT t1.facility_id, t2.aqi_score AS prev_aqi
        FROM latest t1
        JOIN facility_eo_timeseries t2
          ON t2.facility_id = t1.facility_id AND t2.observed_at < t1.observed_at
        WHERE t2.organization_id = :org
        ORDER BY t2.observed_at DESC
      )
      SELECT f.id AS facility_id,
             f.name AS facility_name,
             l.aqi_score AS latest_aqi,
             COALESCE(p.prev_aqi, l.aqi_score) AS prev_aqi
      FROM latest l
      JOIN facilities f ON f.id = l.facility_id
      LEFT JOIN prev p ON p.facility_id = l.facility_id
      ORDER BY l.aqi_score DESC
      LIMIT :limit
    """
    rows = db.execute(text(sql), {"org": org_id, "limit": limit}).mappings().all()
    result = []
    for r in rows:
        latest = float(r["latest_aqi"] or 0)
        prev = float(r["prev_aqi"] or 0)
        delta = latest - prev
        status = "same"
        if delta > 1: status = "worse"
        elif delta < -1: status = "better"
        result.append({
            "facility_id": r["facility_id"],
            "facility_name": r["facility_name"],
            "latest_aqi": latest,
            "prev_aqi": prev,
            "delta_aqi": delta,
            "status": status,
        })
    cache_set(cache_key, result, ttl=600)  # 10 minutes
    return result


