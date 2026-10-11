-- TransportLah PostGIS Spatial Corridor Schema
-- PostgreSQL 15+ with PostGIS Extension

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Transit vehicle positions
CREATE TABLE IF NOT EXISTS vehicle_positions (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(32) NOT NULL,
    service_no VARCHAR(16) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vehicle_positions_geom ON vehicle_positions USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_vehicle_positions_recorded_at ON vehicle_positions (recorded_at);

-- 2. Commuter journey pings
CREATE TABLE IF NOT EXISTS commuter_pings (
    id SERIAL PRIMARY KEY,
    commuter_id VARCHAR(64) NOT NULL,
    ping_id VARCHAR(64) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_commuter_pings_geom ON commuter_pings USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_commuter_pings_recorded_at ON commuter_pings (recorded_at);

-- 3. Corridor matching query function
CREATE OR REPLACE FUNCTION match_transit_corridor(
    p_commuter_id VARCHAR(64),
    p_service_no VARCHAR(16),
    p_max_distance_m FLOAT DEFAULT 100.0,
    p_max_drift_sec FLOAT DEFAULT 30.0
)
RETURNS TABLE (
    ping_id VARCHAR(64),
    vehicle_id VARCHAR(32),
    distance_meters FLOAT,
    drift_seconds FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.ping_id,
        v.vehicle_id,
        ST_Distance(c.geom::geography, v.geom::geography) AS distance_meters,
        abs(EXTRACT(EPOCH FROM (c.recorded_at - v.recorded_at))) AS drift_seconds
    FROM commuter_pings c
    JOIN vehicle_positions v
      ON ST_DWithin(c.geom::geography, v.geom::geography, p_max_distance_m)
     AND abs(EXTRACT(EPOCH FROM (c.recorded_at - v.recorded_at))) <= p_max_drift_sec
    WHERE c.commuter_id = p_commuter_id
      AND v.service_no = p_service_no;
END;
$$ LANGUAGE plpgsql;
