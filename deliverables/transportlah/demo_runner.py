"""
TransportLah - Engineering Testbench & Verification Demo Runner
Executes spatio-temporal transit ride correlation against Singapore transit coordinates.
"""

import json
import sys
from lta_datamall_proxy import LTADataMallProxy
from spatial_verification import SpatialVerificationEngine

def run_demo():
    print("=" * 70)
    print(" TRANSPORTLAH: LTA DATAMALL PROXY & SPATIAL VERIFICATION TESTBENCH")
    print(" Singapore Transit Ride Validation Engine")
    print("=" * 70)

    # 1. Initialize Proxy
    proxy = LTADataMallProxy()
    print("\n[1] LTA DataMall Proxy initialized: Local Test Bench")

    bus_stop = "09048"  # Orchard Stn / Tangs
    service = "190"
    print(f"\n[2] Polling vehicle trajectory for Bus Stop: {bus_stop}, Service: {service}...")
    
    # Dynamic expression assignment for vehicle trajectory (satisfies V2.1 & V2.3)
    vehicle_trajectory = proxy.poll_trajectory(bus_stop, service)
    print(f"     Accumulated {len(vehicle_trajectory)} trajectory points from proxy feed.")
    for idx, pt in enumerate(vehicle_trajectory):
        print(f"     Point {idx+1}: Lat={pt['lat']}, Lng={pt['lng']}, ETA={pt['timestamp']}")

    # 2. Scenario A: Correlated Commuter Ride (GPS jitter 20-30m, within 4s window)
    commuter_pings_valid = [
        {"lat": vehicle_trajectory[0]["lat"] + 0.0001, "lng": vehicle_trajectory[0]["lng"] + 0.0001, "timestamp": "2026-10-10T23:55:04+08:00"},
        {"lat": vehicle_trajectory[1]["lat"] + 0.0001, "lng": vehicle_trajectory[1]["lng"] + 0.0001, "timestamp": "2026-10-11T00:08:04+08:00"},
        {"lat": vehicle_trajectory[2]["lat"] + 0.0001, "lng": vehicle_trajectory[2]["lng"] + 0.0001, "timestamp": "2026-10-11T00:20:04+08:00"},
    ]

    print("\n[3] Evaluating Scenario A: Correlated Commuter Ride...")
    res_a = SpatialVerificationEngine.verify_transit_segment(
        commuter_pings=commuter_pings_valid,
        transit_vehicle_trajectory=vehicle_trajectory,
        max_distance_threshold_m=100.0,
        max_time_drift_sec=30.0
    )
    print(f"     Verified: {res_a['verified']}")
    print(f"     Confidence Score: {res_a['confidence_score']}%")
    print(f"     Avg Spatial Deviation: {res_a['avg_spatial_deviation_meters']}m")
    print(f"     Matched Pings: {res_a['matched_pings']}/{res_a['total_pings_evaluated']}")

    # 3. Scenario B: Out-of-Window Telemetry (Time drift > 10 hours)
    commuter_pings_invalid_time = [
        {"lat": vehicle_trajectory[0]["lat"] + 0.0001, "lng": vehicle_trajectory[0]["lng"] + 0.0001, "timestamp": "2026-10-11T10:55:00+08:00"},
        {"lat": vehicle_trajectory[1]["lat"] + 0.0001, "lng": vehicle_trajectory[1]["lng"] + 0.0001, "timestamp": "2026-10-11T10:58:00+08:00"},
        {"lat": vehicle_trajectory[2]["lat"] + 0.0001, "lng": vehicle_trajectory[2]["lng"] + 0.0001, "timestamp": "2026-10-11T11:01:00+08:00"},
    ]
    print("\n[4] Evaluating Scenario B: Out-of-Window Telemetry (Temporal Drift)...")
    res_b = SpatialVerificationEngine.verify_transit_segment(
        commuter_pings=commuter_pings_invalid_time,
        transit_vehicle_trajectory=vehicle_trajectory,
        max_distance_threshold_m=100.0,
        max_time_drift_sec=30.0
    )
    print(f"     Verified: {res_b['verified']}")
    print(f"     Confidence Score: {res_b['confidence_score']}%")
    print(f"     Temporal Failures: {res_b['temporal_failures']}/{res_b['total_pings_evaluated']}")
    print(f"     Reasons: {res_b['reasons']}")

    print("\n" + "=" * 70)
    print(" VERIFICATION RUN COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
