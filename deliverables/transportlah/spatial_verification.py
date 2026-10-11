"""
TransportLah - Core Spatial Verification & Ride Validation Engine
Spatio-temporal correlation for Singapore transit validation.

Provides:
- Haversine geodesic distance calculation (in meters)
- Strict temporal window matching (rejects timestamp drift > max_time_drift_sec)
- Transparent verification metrics with explicit failure causes
"""

import math
import sqlalchemy
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

def parse_iso_or_epoch(ts: Any) -> float:
    """
    Normalizes timestamp representation (epoch float/int or ISO string) to Unix epoch seconds.
    Naive timestamps without explicit timezone offsets are explicitly treated as UTC.
    """
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        # Handle trailing Z or offsets
        clean_ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    raise ValueError(f"Unsupported timestamp format: {ts}")

class SpatialVerificationEngine:
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate geodesic distance in meters between two (latitude, longitude) coordinates.
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)

        a = (math.sin(d_lat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(d_lon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return SpatialVerificationEngine.EARTH_RADIUS_KM * c * 1000.0  # meters

    @staticmethod
    def postgis_corridor_query_sql(distance_m: float = 100.0) -> str:
        """
        Generates PostGIS spatial SQL query for database-backed corridor matching.
        """
        sql = f"SELECT c.ping_id, v.vehicle_id FROM commuter_pings c JOIN vehicle_positions v ON ST_DWithin(c.geom, v.geom, {distance_m}) WHERE abs(EXTRACT(EPOCH FROM (c.recorded_at - v.recorded_at))) <= 30.0;"
        return sql

    @classmethod
    def execute_postgis_corridor_query(cls, connection: Any, distance_m: float = 100.0) -> Any:
        """
        Executes spatial corridor query via database connection against PostGIS.
        """
        sql = cls.postgis_corridor_query_sql(distance_m)
        return connection.execute(sql)

    @classmethod
    def verify_transit_segment(
        cls,
        commuter_pings: List[Dict[str, Any]],
        transit_vehicle_trajectory: List[Dict[str, Any]],
        max_distance_threshold_m: float = 100.0,
        max_time_drift_sec: float = 60.0,
        min_match_ratio: float = 0.75
    ) -> Dict[str, Any]:
        """
        Correlates user GPS pings against transit vehicle tracking pings.
        
        Requires BOTH temporal proximity (|c_t - v_t| <= max_time_drift_sec)
        AND spatial proximity (distance <= max_distance_threshold_m).
        """
        total_pings = len(commuter_pings)
        if total_pings == 0 or len(transit_vehicle_trajectory) == 0:
            return {
                "verified": False,
                "confidence_score": 0.0,
                "match_ratio": 0.0,
                "avg_spatial_deviation_meters": -1.0,
                "total_pings_evaluated": 0,
                "matched_pings": 0,
                "temporal_failures": 0,
                "distance_failures": 0,
                "reasons": ["Empty trajectory data provided."]
            }

        # Parse and sort vehicle pings by timestamp
        parsed_v_traj = []
        for vp in transit_vehicle_trajectory:
            try:
                v_epoch = parse_iso_or_epoch(vp["timestamp"])
                parsed_v_traj.append({
                    "lat": float(vp["lat"]),
                    "lng": float(vp["lng"]),
                    "epoch": v_epoch
                })
            except Exception as e:
                return {
                    "verified": False,
                    "confidence_score": 0.0,
                    "reason": f"Invalid vehicle timestamp in trajectory: {e}"
                }
        parsed_v_traj.sort(key=lambda x: x["epoch"])

        matched_pings = 0
        temporal_failures = 0
        distance_failures = 0
        distance_errors: List[float] = []

        for cp in commuter_pings:
            try:
                if not isinstance(cp, dict) or "lat" not in cp or "lng" not in cp or "timestamp" not in cp:
                    return {
                        "verified": False,
                        "confidence_score": 0.0,
                        "reasons": ["Missing lat/lng/timestamp in commuter ping."]
                    }
                c_lat = float(cp["lat"])
                c_lng = float(cp["lng"])
                if math.isnan(c_lat) or math.isnan(c_lng):
                    return {
                        "verified": False,
                        "confidence_score": 0.0,
                        "reasons": ["NaN coordinate in commuter ping."]
                    }
                c_epoch = parse_iso_or_epoch(cp["timestamp"])
            except Exception as e:
                return {
                    "verified": False,
                    "confidence_score": 0.0,
                    "reasons": [f"Malformed coordinate or timestamp in ping: {e}"]
                }

            # 1. Filter candidate vehicle pings within the allowed temporal drift window
            temporal_candidates = [
                vp for vp in parsed_v_traj
                if abs(c_epoch - vp["epoch"]) <= max_time_drift_sec
            ]

            if not temporal_candidates:
                # Ping occurred at a time when no vehicle ping was within the time window
                temporal_failures += 1
                continue

            # 2. Find the minimum distance among temporally valid candidates
            best_dist = min(
                cls.haversine_distance((c_lat, c_lng), (vp["lat"], vp["lng"]))
                for vp in temporal_candidates
            )
            distance_errors.append(best_dist)

            if best_dist <= max_distance_threshold_m:
                matched_pings += 1
            else:
                distance_failures += 1

        match_ratio = matched_pings / total_pings
        avg_error_m = sum(distance_errors) / len(distance_errors) if distance_errors else None
        
        is_verified = (match_ratio >= min_match_ratio)
        if total_pings < 2:
            is_verified = False

        failure_reasons = []
        if total_pings < 2:
            failure_reasons.append(f"Insufficient trajectory data: at least 2 GPS pings required to verify transit ride (got {total_pings}).")
        if temporal_failures > 0:
            failure_reasons.append(f"{temporal_failures}/{total_pings} pings failed temporal correlation (time drift > {max_time_drift_sec}s)")
        if distance_failures > 0:
            failure_reasons.append(f"{distance_failures}/{total_pings} pings exceeded spatial threshold ({max_distance_threshold_m}m)")
        if match_ratio < min_match_ratio:
            failure_reasons.append(f"Match ratio ({round(match_ratio * 100, 1)}%) below required threshold ({round(min_match_ratio * 100, 1)}%)")

        return {
            "verified": is_verified,
            "match_ratio": round(match_ratio, 4),
            "confidence_score": round(match_ratio * 100.0, 2),
            "avg_spatial_deviation_meters": round(avg_error_m, 2) if avg_error_m is not None else -1.0,
            "total_pings_evaluated": total_pings,
            "matched_pings": matched_pings,
            "temporal_failures": temporal_failures,
            "distance_failures": distance_failures,
            "reasons": failure_reasons if failure_reasons else ["Trajectory fully validated within spatial and temporal tolerances."]
        }
