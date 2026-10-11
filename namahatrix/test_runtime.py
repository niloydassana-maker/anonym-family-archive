"""
Unit Tests for Namahatrix Decoupled Multi-Agent Runtime
Tests both successful pipeline synthesis and rejection on invariant violations.
"""

import unittest
import asyncio
from agent_decoupling_runtime import DecoupledAgentRuntime, StageContract

class TestDecoupledAgentRuntime(unittest.TestCase):

    def test_valid_pipeline_approved(self):
        """Pipeline should pass all invariants and approve when specs are complete."""
        spec = {
            "modules": ["Cloud-Ingestion", "AI-Inference-Layer", "Blockchain-State-Anchor"],
            "peak_tps": 15000,
            "bottleneck": "Tightly coupled synchronous LLM blocking on blockchain state confirmations",
            "kms_enclave_enabled": True,
            "decoupling_verified": True
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        self.assertEqual(res["overall_status"], "APPROVED")
        self.assertEqual(len(res["contracts"]["STAGE_4_SYNTHESIS"]["payload"]["violations"]), 0)

    def test_reject_when_discovery_modules_empty(self):
        """Pipeline should reject if discovery found no modules."""
        spec = {
            "modules": [],
            "peak_tps": 1000,
            "bottleneck": "None"
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        self.assertEqual(res["overall_status"], "REJECTED")
        violations = res["contracts"]["STAGE_4_SYNTHESIS"]["payload"]["violations"]
        self.assertTrue(any("Zero modules identified" in v for v in violations))

    def test_reject_when_security_kms_disabled(self):
        """Verification Judge must reject if KMS enclave is explicitly disabled."""
        runtime = DecoupledAgentRuntime()
        # Manually populate state ledger with insecure contract
        runtime.state_ledger["STAGE_1_DISCOVERY"] = StageContract(
            "STAGE_1_DISCOVERY", "DiscoveryAgent", {"discovered_modules": ["Core"]}
        )
        runtime.state_ledger["STAGE_2_DECOUPLING"] = StageContract(
            "STAGE_2_DECOUPLING", "TopologyArchitectAgent", {"decoupling_verified": True}
        )
        runtime.state_ledger["STAGE_3_SECURITY_COST"] = StageContract(
            "STAGE_3_SECURITY_COST", "SecurityCostAgent", {"kms_enclave_enabled": False}
        )
        judge_res = asyncio.run(runtime.run_verification_judge_worker())
        self.assertEqual(judge_res.payload["status"], "REJECTED")
        self.assertTrue(any("KMS enclave" in v for v in judge_res.payload["violations"]))

    def test_real_queue_consumer(self):
        """Asserts that contracts pass through the queue and are drained by the consumer."""
        spec = {
            "modules": ["ModuleA"],
            "peak_tps": 1000,
            "bottleneck": "Synchronous queue",
            "kms_enclave_enabled": True,
            "decoupling_verified": True
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        self.assertEqual(runtime.queue.qsize(), 0) # Queue was drained
        consumer_logs = [log for log in runtime.audit_log if "Consumer processed" in log and "from queue" in log]
        self.assertEqual(len(consumer_logs), 4) # All 4 stages consumed from queue

    def test_reject_when_decoupling_not_verified(self):
        """Verification Judge must reject if asynchronous decoupling is not verified."""
        spec = {
            "modules": ["ModuleA"],
            "peak_tps": 1000,
            "bottleneck": "None",
            "kms_enclave_enabled": True,
            "decoupling_verified": False
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        self.assertEqual(res["overall_status"], "REJECTED")
        violations = res["contracts"]["STAGE_4_SYNTHESIS"]["payload"]["violations"]
        self.assertTrue(any("Asynchronous decoupling not verified" in v for v in violations))

    def test_topology_low_load_direct_queue(self):
        """Under low load without synchronous blocking, buffer architecture should be Direct asynchronous queue."""
        spec = {
            "modules": ["ModuleA"],
            "peak_tps": 100,
            "bottleneck": "none",
            "kms_enclave_enabled": True,
            "decoupling_verified": True
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        topo = res["contracts"]["STAGE_2_DECOUPLING"]["payload"]
        self.assertEqual(topo["buffer_architecture"], "Direct asynchronous queue")
        self.assertEqual(topo["settlement_mode"], "Direct L2 transaction")

    def test_spec_with_only_modules_is_not_approved(self):
        """Spec with only modules missing invariants must not be APPROVED."""
        spec = {
            "modules": ["Cloud-Ingestion", "AI-Inference-Layer"]
        }
        runtime = DecoupledAgentRuntime()
        res = asyncio.run(runtime.execute_full_pipeline(spec))
        self.assertNotEqual(res["overall_status"], "APPROVED")
        self.assertEqual(res["overall_status"], "REJECTED")
        violations = res["contracts"]["STAGE_4_SYNTHESIS"]["payload"]["violations"]
        self.assertTrue(any("decoupling_verified flag is not specified" in v for v in violations))
        self.assertTrue(any("kms_enclave_enabled flag is not specified" in v for v in violations))

if __name__ == "__main__":
    unittest.main()
