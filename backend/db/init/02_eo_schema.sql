CREATE TABLE IF NOT EXISTS facility_eo_timeseries (
  organization_id TEXT NOT NULL,
  facility_id TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  geom geometry(Point, 4326),
  aqi_score NUMERIC,
  no2 DOUBLE PRECISION,
  co DOUBLE PRECISION,
  so2 DOUBLE PRECISION,
  o3 DOUBLE PRECISION,
  ch4 DOUBLE PRECISION,
  aod DOUBLE PRECISION,
  source TEXT,
  window_km NUMERIC,
  raw_payload JSONB,
  PRIMARY KEY (organization_id, facility_id, observed_at)
);

-- Convert to hypertable
SELECT create_hypertable('facility_eo_timeseries', 'observed_at', if_not_exists => TRUE);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS ix_eo_org ON facility_eo_timeseries (organization_id);
CREATE INDEX IF NOT EXISTS ix_eo_facility ON facility_eo_timeseries (facility_id);
CREATE INDEX IF NOT EXISTS ix_eo_observed_at ON facility_eo_timeseries (observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_eo_geom ON facility_eo_timeseries USING GIST (geom);


