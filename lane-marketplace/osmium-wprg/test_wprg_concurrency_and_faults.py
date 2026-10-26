"""Reproducible Test Suite for Enterprise Webhook Ingestion & Payment Reconciliation Gateway (WPRG)
Vendor: Xsolve Systems
Verification Standard: 100% genuine execution, zero simulated results, deterministic invariants.
"""

import unittest
import time
import json
import hmac
import hashlib
import concurrent.futures
from wprg_gateway import WPRGCoreEngine, PaymentState

TEST_SECRET = "osmium_test_secret_key_xsolve_systems_2026"

def generate_signed_request(secret: str, payload_dict: dict, timestamp_offset: float = 0.0):
    raw_body = json.dumps(payload_dict).encode('utf-8')
    ts = str(time.time() + timestamp_offset)
    payload_to_sign = f"{ts}.".encode('utf-8') + raw_body
    sig = hmac.new(secret.encode('utf-8'), payload_to_sign, hashlib.sha256).hexdigest()
    return raw_body, sig, ts

class TestWPRGReliabilityEcosystem(unittest.TestCase):
    
    def setUp(self):
        self.engine = WPRGCoreEngine(webhook_secret=TEST_SECRET, max_drift_seconds=300)

    def test_01_duplicate_event_concurrency(self):
        """Test: 100 simultaneous concurrent threads delivering the exact same event ID."""
        event_payload = {
            "event_id": "evt_concurrent_race_001",
            "order_id": "ord_enterprise_9981",
            "state": "INITIATED",
            "amount_cents": 50000,
            "currency": "USD"
        }
        raw_body, sig, ts = generate_signed_request(TEST_SECRET, event_payload)

        # Run 100 parallel concurrent worker calls
        concurrency_count = 100
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(self.engine.process_incoming_webhook, raw_body, sig, ts)
                for _ in range(concurrency_count)
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        processed_count = sum(1 for r in results if r["status"] == "PROCESSED")
        idempotent_suppressed = sum(1 for r in results if r["status"] == "IDEMPOTENT_HIT")
        
        self.assertEqual(processed_count, 1, "Exactly 1 concurrent request must acquire lock and process")
        self.assertEqual(idempotent_suppressed, 99, "99 concurrent duplicate requests must be suppressed")
        
        # Verify ledger state
        ledger = self.engine.get_ledger_state("ord_enterprise_9981")
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger["current_state"], "INITIATED")
        self.assertEqual(ledger["version"], 1, "Ledger version must be exactly 1 (zero double-transitions)")

    def test_02_signature_and_timestamp_rejections(self):
        """Test: Cryptographic integrity and timestamp replay attacks."""
        valid_payload = {
            "event_id": "evt_auth_001",
            "order_id": "ord_auth_001",
            "state": "INITIATED",
            "amount_cents": 25000,
            "currency": "USD"
        }
        
        # 1. Valid Signature -> Must PASS (200)
        raw_body, valid_sig, ts = generate_signed_request(TEST_SECRET, valid_payload)
        res = self.engine.process_incoming_webhook(raw_body, valid_sig, ts)
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["status"], "PROCESSED")

        # 2. Tampered Signature -> Must REJECT (401)
        tampered_sig = valid_sig[:-4] + "ffff"
        res_tampered = self.engine.process_incoming_webhook(raw_body, tampered_sig, ts)
        self.assertEqual(res_tampered["status_code"], 401)
        self.assertIn("cryptographic signature mismatch", res_tampered["error"].lower())

        # 3. Timestamp Replay Attack (> 300s drift in past) -> Must REJECT (400)
        raw_past, sig_past, ts_past = generate_signed_request(TEST_SECRET, valid_payload, timestamp_offset=-350.0)
        res_past = self.engine.process_incoming_webhook(raw_past, sig_past, ts_past)
        self.assertEqual(res_past["status_code"], 400)
        self.assertIn("drift exceeds tolerance", res_past["error"].lower())

        # 4. Future Timestamp Spoofing (> 300s drift in future) -> Must REJECT (400)
        raw_future, sig_future, ts_future = generate_signed_request(TEST_SECRET, valid_payload, timestamp_offset=350.0)
        res_future = self.engine.process_incoming_webhook(raw_future, sig_future, ts_future)
        self.assertEqual(res_future["status_code"], 400)
        self.assertIn("drift exceeds tolerance", res_future["error"].lower())

    def test_03_out_of_order_recovery(self):
        """Test: Event arrival out-of-order (SETTLED arriving before INITIATED)."""
        order_id = "ord_ooo_7712"
        
        # Out-of-order event: SETTLED arrives first
        evt_settled = {
            "event_id": "evt_ooo_settled",
            "order_id": order_id,
            "state": "SETTLED",
            "amount_cents": 120000,
            "currency": "USD"
        }
        raw_s, sig_s, ts_s = generate_signed_request(TEST_SECRET, evt_settled)
        res_s = self.engine.process_incoming_webhook(raw_s, sig_s, ts_s)
        
        # Must be staged, not blindly credited
        self.assertEqual(res_s["status_code"], 200)
        self.assertEqual(res_s["resolution"]["state"], "STAGED_OUT_OF_ORDER")
        self.assertIsNone(self.engine.get_ledger_state(order_id), "Ledger must not premature credit")

        # Now the initial event arrives: INITIATED
        evt_init = {
            "event_id": "evt_ooo_init",
            "order_id": order_id,
            "state": "INITIATED",
            "amount_cents": 120000,
            "currency": "USD"
        }
        raw_i, sig_i, ts_i = generate_signed_request(TEST_SECRET, evt_init)
        res_i = self.engine.process_incoming_webhook(raw_i, sig_i, ts_i)
        self.assertEqual(res_i["status_code"], 200)
        
        # Sequence: Intermediate AUTHORIZED arrives
        evt_auth = {
            "event_id": "evt_ooo_auth",
            "order_id": order_id,
            "state": "AUTHORIZED",
            "amount_cents": 120000,
            "currency": "USD"
        }
        raw_a, sig_a, ts_a = generate_signed_request(TEST_SECRET, evt_auth)
        self.engine.process_incoming_webhook(raw_a, sig_a, ts_a)

        # Intermediate CAPTURED arrives -> Drains the buffered SETTLED automatically
        evt_cap = {
            "event_id": "evt_ooo_cap",
            "order_id": order_id,
            "state": "CAPTURED",
            "amount_cents": 120000,
            "currency": "USD"
        }
        raw_c, sig_c, ts_c = generate_signed_request(TEST_SECRET, evt_cap)
        self.engine.process_incoming_webhook(raw_c, sig_c, ts_c)

        # Final assertion: The buffered SETTLED event drained cleanly, final balance is 120000 cents
        ledger = self.engine.get_ledger_state(order_id)
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger["current_state"], "SETTLED")
        self.assertEqual(ledger["amount_credited_cents"], 120000)

    def test_04_retry_and_dead_letter_quarantine(self):
        """Test: Downstream database/service outage routes event to DLQ without data loss."""
        fail_payload = {
            "event_id": "evt_dlq_test_01",
            "order_id": "ord_failover_009",
            "state": "INITIATED",
            "amount_cents": 7500,
            "currency": "USD"
        }
        raw_body, sig, ts = generate_signed_request(TEST_SECRET, fail_payload)
        
        # Simulate downstream failure
        res = self.engine.process_incoming_webhook(raw_body, sig, ts, simulated_downstream_failure=True)
        self.assertEqual(res["status_code"], 202)
        self.assertEqual(res["status"], "ROUTED_TO_DLQ")
        
        # Assert DLQ presence
        self.assertEqual(len(self.engine.dead_letter_queue), 1)
        dlq_entry = self.engine.dead_letter_queue[0]
        self.assertEqual(dlq_entry["event"].event_id, "evt_dlq_test_01")
        self.assertEqual(dlq_entry["reason"], "Simulated downstream target unavailable")

    def test_05_sub_30ms_latency_benchmark(self):
        """Test: Benchmark acknowledgment latency across 1,000 verified requests."""
        latencies = []
        for i in range(1000):
            payload = {
                "event_id": f"evt_bench_{i}",
                "order_id": f"ord_bench_{i}",
                "state": "INITIATED",
                "amount_cents": 1000,
                "currency": "USD"
            }
            raw_body, sig, ts = generate_signed_request(TEST_SECRET, payload)
            res = self.engine.process_incoming_webhook(raw_body, sig, ts)
            latencies.append(res["latency_ms"])
            
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        avg = sum(latencies) / len(latencies)
        
        print(f"\n--- LATENCY BENCHMARK (1,000 Requests) ---")
        print(f"Mean Latency: {avg:.3f} ms")
        print(f"P50:          {p50:.3f} ms")
        print(f"P95:          {p95:.3f} ms")
        print(f"P99:          {p99:.3f} ms")
        print(f"Max:          {latencies[-1]:.3f} ms")
        print(f"------------------------------------------\n")
        
        self.assertLess(p99, 30.0, "99th percentile acknowledgment latency must be strictly under 30ms")

if __name__ == "__main__":
    unittest.main()
