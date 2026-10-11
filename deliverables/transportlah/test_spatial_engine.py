"""
Test Suite for TransportLah Spatial Verification Engine
Runs positive verification and negative failure mode assertions.
"""

import unittest
from spatial_verification import SpatialVerificationEngine

class TestSpatialVerificationEngine(unittest.TestCase):

    def setUp(self):
        # Realistic SMRT Bus 190 Route Segment (Orchard -> Somerset -> Dhoby Ghaut)
        self.bus_trajectory = [
            {"lat": 1.3048, "lng": 103.8318, "timestamp": "2026-10-10T23:55:00Z"},
            {"lat": 1.3015, "lng": 103.8385, "timestamp": "2026-10-10T23:58:00Z"},
            {"lat": 1.2990, "lng": 103.8450, "timestamp": "2026-10-11T00:01:00Z"},
        ]

    def test_valid_ride_correlated(self):
        """User pings match bus trajectory within 5 seconds and 30 meters."""
        commuter_pings = [
            {"lat": 1.3049, "lng": 103.8319, "timestamp": "2026-10-10T23:55:04Z"},
            {"lat": 1.3017, "lng": 103.8387, "timestamp": "2026-10-10T23:58:03Z"},
            {"lat": 1.2992, "lng": 103.8452, "timestamp": "2026-10-11T00:01:05Z"},
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            commuter_pings, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=30.0
        )
        self.assertTrue(res["verified"])
        self.assertEqual(res["matched_pings"], 3)
        self.assertEqual(res["temporal_failures"], 0)
        self.assertEqual(res["distance_failures"], 0)
        self.assertLess(res["avg_spatial_deviation_meters"], 40.0)

    def test_fail_temporal_drift_12_hours_later(self):
        """User coordinates match locations, but occurred 12 hours later."""
        commuter_pings = [
            {"lat": 1.3049, "lng": 103.8319, "timestamp": "2026-10-11T11:55:00Z"},
            {"lat": 1.3017, "lng": 103.8387, "timestamp": "2026-10-11T11:58:00Z"},
            {"lat": 1.2992, "lng": 103.8452, "timestamp": "2026-10-11T12:01:00Z"},
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            commuter_pings, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=60.0
        )
        self.assertFalse(res["verified"])
        self.assertEqual(res["matched_pings"], 0)
        self.assertEqual(res["temporal_failures"], 3)

    def test_fail_spatial_divergence(self):
        """User was in London while bus was in Singapore."""
        commuter_pings = [
            {"lat": 51.5074, "lng": -0.1278, "timestamp": "2026-10-10T23:55:00Z"}
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            commuter_pings, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=60.0
        )
        self.assertFalse(res["verified"])
        self.assertEqual(res["distance_failures"], 1)

    def test_fail_empty_trajectory(self):
        """Empty input should fail gracefully."""
        res = SpatialVerificationEngine.verify_transit_segment([], self.bus_trajectory)
        self.assertFalse(res["verified"])
        self.assertEqual(res["confidence_score"], 0.0)

    def test_naive_timestamp_treated_as_utc(self):
        """
        Commuter submits naive ISO string '2026-10-10T23:55:04' (intended as UTC).
        Bus has '2026-10-10T23:55:00Z'.
        Under TZ=Asia/Kolkata, naive timestamp without explicit UTC treatment drifts
        by 19,800 seconds (5h 30m) and fails.
        """
        commuter_pings = [
            {"lat": 1.3049, "lng": 103.8319, "timestamp": "2026-10-10T23:55:04"},
            {"lat": 1.3017, "lng": 103.8387, "timestamp": "2026-10-10T23:58:03"},
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            commuter_pings, self.bus_trajectory, max_time_drift_sec=30.0
        )
        self.assertTrue(res["verified"], f"Naive timestamp was not treated as UTC. Failures: {res.get('reasons')}")

    def test_single_ping_ride_rejected(self):
        """
        A commuter submitting only a single GPS ping is rejected.
        Start and end of a transit ride cannot be shown by one ping.
        """
        single_ping = [
            {"lat": 1.3048, "lng": 103.8318, "timestamp": "2026-10-10T23:55:00Z"}
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            single_ping, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=30.0
        )
        self.assertFalse(res["verified"])
        self.assertEqual(res["total_pings_evaluated"], 1)

    def test_known_limit_90m_pedestrian(self):
        """
        KNOWN LIMIT: A pedestrian walking on the pavement 90m away from the bus
        passes verification because the corridor tolerance threshold is 100m.
        The engine cannot distinguish a nearby pedestrian from an onboard passenger.
        """
        # 1.3048 lat + 0.0008 lat is approximately 88.9 meters away
        pedestrian_pings = [
            {"lat": 1.3048 + 0.0008, "lng": 103.8318, "timestamp": "2026-10-10T23:55:05Z"},
            {"lat": 1.3015 + 0.0008, "lng": 103.8385, "timestamp": "2026-10-10T23:58:05Z"},
            {"lat": 1.2990 + 0.0008, "lng": 103.8450, "timestamp": "2026-10-11T00:01:05Z"},
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            pedestrian_pings, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=30.0
        )
        self.assertTrue(res["verified"])
        self.assertGreater(res["avg_spatial_deviation_meters"], 80.0)
        self.assertLessEqual(res["avg_spatial_deviation_meters"], 100.0)

    def test_known_limit_replayed_bus_coordinates(self):
        """
        KNOWN LIMIT: Replaying exact vehicle coordinates directly from the public
        transit API with a small timestamp jitter passes verification (100% confidence).
        The engine cannot detect software spoofing without hardware device attestation.
        """
        spoofed_replayed_pings = [
            {"lat": vp["lat"], "lng": vp["lng"], "timestamp": vp["timestamp"]}
            for vp in self.bus_trajectory
        ]
        res = SpatialVerificationEngine.verify_transit_segment(
            spoofed_replayed_pings, self.bus_trajectory, max_distance_threshold_m=100.0, max_time_drift_sec=30.0
        )
        self.assertTrue(res["verified"])
        self.assertEqual(res["confidence_score"], 100.0)
        self.assertEqual(res["avg_spatial_deviation_meters"], 0.0)

if __name__ == "__main__":
    unittest.main()
