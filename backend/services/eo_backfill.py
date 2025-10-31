from __future__ import annotations

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import Iterator, Optional

from sqlalchemy import text
import logging
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from db.models import Facility


def _month_floor(dt: datetime) -> datetime:
    dt = dt.astimezone(timezone.utc)
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_iter(start: datetime, end: datetime) -> Iterator[datetime]:
    """Yield first-of-month instants from start to end inclusive."""
    cur = _month_floor(start)
    last = _month_floor(end)
    while cur <= last:
        yield cur
        cur = cur + relativedelta(months=1)


def _ensure_table(db: Session) -> None:
    # Create table and indexes if not present. Works without Timescale; compatible if Timescale exists.
    db.execute(text(
        """
        CREATE TABLE IF NOT EXISTS facility_eo_timeseries (
          organization_id   varchar NOT NULL,
          facility_id       varchar NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
          observed_at       timestamptz NOT NULL,
          geom              geometry(Point, 4326),
          aqi_score         numeric,
          no2               numeric,
          co                numeric,
          so2               numeric,
          o3                numeric,
          ch4               numeric,
          aod               numeric,
          source            text,
          window_km         numeric,
          raw_payload       jsonb,
          PRIMARY KEY (organization_id, facility_id, observed_at)
        );
        """
    ))
    db.execute(text("CREATE INDEX IF NOT EXISTS feo_observed_at_brin ON facility_eo_timeseries USING brin (observed_at);"))
    db.execute(text("CREATE INDEX IF NOT EXISTS feo_facility_btree   ON facility_eo_timeseries (facility_id, observed_at DESC);"))
    db.execute(text("CREATE INDEX IF NOT EXISTS feo_geom_gist        ON facility_eo_timeseries USING gist (geom);"))
    logging.debug("[EO_BACKFILL] ensured table & indexes")


def _synthetic_values(seed_key: str) -> tuple[float, float, float, float, float, float, float]:
    import random
    r = random.Random(seed_key)
    aqi = round(r.uniform(60, 150), 1)
    no2 = round(r.uniform(1.0e-5, 4.0e-5), 7)
    co  = round(r.uniform(0.1, 0.8), 3)
    so2 = round(r.uniform(0.001, 0.02), 4)
    o3  = round(r.uniform(0.02, 0.09), 3)
    ch4 = round(r.uniform(1.7, 2.3), 3)
    aod = round(r.uniform(0.05, 0.6), 3)
    return aqi, no2, co, so2, o3, ch4, aod


def _observed_bounds(db: Session, organization_id: str, facility_id: str) -> tuple[Optional[datetime], Optional[datetime]]:
    row = db.execute(text(
        """
        SELECT MIN(observed_at) AS first_ts, MAX(observed_at) AS last_ts
        FROM facility_eo_timeseries
        WHERE organization_id=:org AND facility_id=:fid
        """
    ), {"org": organization_id, "fid": facility_id}).first()
    if not row:
        return None, None
    return row.first_ts, row.last_ts


def backfill_facility(db: Session, organization_id: str, facility: Facility,
                      months_before: int = 6, window_km: float = 5.0,
                      source: str = "synthetic_backfill") -> int:
    """
    Generate one EO record per month from 6 months before the facility's first record
    until its latest existing EO month (or today if none).
    Returns number of upserts.
    """
    _ensure_table(db)

    first_eo, last_eo = _observed_bounds(db, organization_id, facility.id)
    base = first_eo or getattr(facility, "created_at", None) or datetime.now(timezone.utc)
    start = _month_floor(base) - relativedelta(months=months_before)
    end = _month_floor(last_eo or datetime.now(timezone.utc))

    lat = lon = None
    if facility.location:
        p = to_shape(facility.location)
        lat, lon = p.y, p.x

    count = 0
    for ts in _month_iter(start, end):
        seed = f"{organization_id}:{facility.id}:{ts.strftime('%Y-%m')}"
        aqi, no2, co, so2, o3, ch4, aod = _synthetic_values(seed)
        db.execute(text(
            """
            INSERT INTO facility_eo_timeseries (
              organization_id, facility_id, observed_at, geom,
              aqi_score, no2, co, so2, o3, ch4, aod, source, window_km, raw_payload
            ) VALUES (
              :org, :fid, :ts,
              CASE WHEN :lon IS NULL OR :lat IS NULL THEN NULL
                   ELSE ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) END,
              :aqi, :no2, :co, :so2, :o3, :ch4, :aod, :source, :win,
              CAST(:payload AS jsonb)
            )
            ON CONFLICT (organization_id, facility_id, observed_at) DO UPDATE SET
              aqi_score = EXCLUDED.aqi_score,
              no2 = EXCLUDED.no2,
              co = EXCLUDED.co,
              so2 = EXCLUDED.so2,
              o3 = EXCLUDED.o3,
              ch4 = EXCLUDED.ch4,
              aod = EXCLUDED.aod,
              source = EXCLUDED.source,
              window_km = EXCLUDED.window_km,
              raw_payload = EXCLUDED.raw_payload
            """
        ), {
            "org": organization_id, "fid": facility.id, "ts": ts,
            "lon": lon, "lat": lat,
            "aqi": aqi, "no2": no2, "co": co, "so2": so2, "o3": o3, "ch4": ch4, "aod": aod,
            "source": source, "win": window_km,
            "payload": '{"note":"synthetic monthly backfill"}'
        })
        count += 1
    logging.info(f"[EO_BACKFILL] facility={facility.id} rows_upserted={count}")
    return count


def backfill_all_facilities(db: Session, organization_id: str, months_before: int = 6) -> dict:
    facilities = db.query(Facility).filter(Facility.organization_id == organization_id).all()
    total_rows = 0
    for f in facilities:
        total_rows += backfill_facility(db, organization_id, f, months_before=months_before)
    db.commit()
    logging.info(f"[EO_BACKFILL] org={organization_id} facilities={len(facilities)} rows={total_rows}")
    return {"facilities": len(facilities), "rows": total_rows}


