"""
Namahatrix - Decoupled Multi-Agent Architecture Runtime & Pipeline Engine
Provides asynchronous queue-based agent orchestration with real producer/consumer loops.

Key Mechanisms:
- Asynchronous FIFO queue message bus with dedicated background consumer worker
- Isolated worker execution boundaries (typed contracts between stages)
- VerificationJudge evaluating architectural invariants (fails if constraints are violated)
"""

import asyncio
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

@dataclass
class StageContract:
    stage_id: str
    producer_agent: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    schema_version: str = "1.0.0"

class DecoupledAgentRuntime:
    """
    Asynchronous event-driven agent runtime implementing decoupled worker pipelines.
    """
    def __init__(self, system_name: str = "Namahatrix-Core"):
        self.system_name = system_name
        self.queue: asyncio.Queue[StageContract] = asyncio.Queue()
        self.state_ledger: Dict[str, StageContract] = {}
        self.audit_log: List[str] = []

    async def emit_contract(self, contract: StageContract) -> None:
        """Pushes an executed stage contract onto the decoupled message queue."""
        await self.queue.put(contract)
        self.audit_log.append(f"[{time.strftime('%H:%M:%S')}] Enqueued {contract.stage_id} from {contract.producer_agent}")

    async def queue_consumer_worker(self) -> None:
        """
        Real background consumer consuming contracts from the FIFO queue,
        persisting verified state into state_ledger, and dispatching subsequent pipeline workers.
        """
        while True:
            contract = await self.queue.get()
            self.state_ledger[contract.stage_id] = contract
            self.audit_log.append(f"[{time.strftime('%H:%M:%S')}] Consumer processed {contract.stage_id} from queue")

            try:
                if contract.stage_id == "STAGE_1_DISCOVERY":
                    # Consumer routes discovery output to Topology Worker
                    await self.run_topology_worker(contract)
                elif contract.stage_id == "STAGE_2_DECOUPLING":
                    # Consumer routes topology output to Security & Cost Worker
                    await self.run_security_cost_worker(contract)
                elif contract.stage_id == "STAGE_3_SECURITY_COST":
                    # Consumer routes to Verification Judge
                    await self.run_verification_judge_worker()
                elif contract.stage_id == "STAGE_4_SYNTHESIS":
                    # Terminal contract reached
                    self.queue.task_done()
                    break
            finally:
                if contract.stage_id != "STAGE_4_SYNTHESIS":
                    self.queue.task_done()

    # --- Worker 1: Discovery Worker ---
    async def run_discovery_worker(self, system_spec: Dict[str, Any]) -> StageContract:
        modules = system_spec.get("modules", [])
        peak_tps = system_spec.get("peak_tps", 0)
        bottleneck = system_spec.get("bottleneck", "None detected")

        kms_enabled = system_spec.get("kms_enclave_enabled")
        if kms_enabled is None and isinstance(system_spec.get("security"), dict):
            kms_enabled = system_spec["security"].get("kms")
        # Defaults to None if missing in spec

        decoupling_verified = system_spec.get("decoupling_verified")
        # Defaults to None if missing in spec

        payload = {
            "discovered_modules": modules,
            "peak_tps": peak_tps,
            "current_bottleneck": bottleneck,
            "synchronous_blocking_detected": ("synchronous" in bottleneck.lower()),
            "kms_enclave_enabled": kms_enabled,
            "decoupling_verified": decoupling_verified
        }
        contract = StageContract("STAGE_1_DISCOVERY", "DiscoveryAgent", payload)
        await self.emit_contract(contract)
        return contract

    # --- Worker 2: Topology Architect Worker ---
    async def run_topology_worker(self, discovery_contract: StageContract) -> StageContract:
        disc_payload = discovery_contract.payload
        sync_blocking = disc_payload.get("synchronous_blocking_detected", False)
        peak_tps = disc_payload.get("peak_tps", 0)
        decoupling_verified = disc_payload.get("decoupling_verified")
        kms_enclave_enabled = disc_payload.get("kms_enclave_enabled")

        if peak_tps > 5000 or sync_blocking:
            buffer_arch = "Event-driven asynchronous buffer (Redis Streams / Kafka) decoupling inference from L2 rollup"
            settlement_mode = "Optimistic batch state settlement"
        else:
            buffer_arch = "Direct asynchronous queue"
            settlement_mode = "Direct L2 transaction"

        payload = {
            "buffer_architecture": buffer_arch,
            "settlement_mode": settlement_mode,
            "inference_cluster": "Ray distributed cluster with auto-scaling spot nodes",
            "peak_tps": peak_tps,
            "decoupling_verified": decoupling_verified,
            "kms_enclave_enabled": kms_enclave_enabled
        }
        contract = StageContract("STAGE_2_DECOUPLING", "TopologyArchitectAgent", payload)
        await self.emit_contract(contract)
        return contract

    # --- Worker 3: Security & Cost Worker ---
    async def run_security_cost_worker(self, topology_contract: StageContract) -> StageContract:
        topo_payload = topology_contract.payload
        peak_tps = topo_payload.get("peak_tps", 100)
        kms_enclave_enabled = topo_payload.get("kms_enclave_enabled", True)

        # Named inputs & rates [ASSUMPTIONS]
        gpu_rate_usd_per_hr = 1.50   # [ASSUMPTION: RunPod / Lambda 1x A10G spot, Oct 2026]
        cpu_rate_usd_per_hr = 0.10   # [ASSUMPTION: AWS c6g.large on-demand, Oct 2026]
        broker_base_usd_per_mo = 150.0 # [ASSUMPTION: AWS Managed Redis/Kafka base tier, Oct 2026]
        kms_base_usd_per_mo = 50.0   # [ASSUMPTION: AWS KMS CloudHSM tier, Oct 2026]
        hours_per_month = 720.0

        # Continuous smooth cost formula (no step cliffs)
        # Pilot tier: base broker + KMS + active development GPU & worker CPU hours
        tps = max(1, peak_tps)
        gpu_hours_pilot = 120.0 + (tps / 50000.0) * 360.0
        cpu_hours_pilot = 720.0
        pilot_cost = round(broker_base_usd_per_mo + kms_base_usd_per_mo + (gpu_hours_pilot * gpu_rate_usd_per_hr) + (cpu_hours_pilot * cpu_rate_usd_per_hr), 2)

        # Scale tier: 24/7 cluster scaling with throughput
        gpu_instances = 1.0 + (tps / 5000.0)
        gpu_hours_scale = gpu_instances * hours_per_month
        cpu_instances = 2.0 + (tps / 10000.0)
        cpu_hours_scale = cpu_instances * hours_per_month
        broker_scale_usd_per_mo = broker_base_usd_per_mo + (tps / 1000.0) * 10.0
        scale_cost = round(broker_scale_usd_per_mo + kms_base_usd_per_mo + (gpu_hours_scale * gpu_rate_usd_per_hr) + (cpu_hours_scale * cpu_rate_usd_per_hr), 2)

        cost_inputs = {
            "gpu_rate_usd_per_hr": gpu_rate_usd_per_hr,
            "cpu_rate_usd_per_hr": cpu_rate_usd_per_hr,
            "broker_base_usd_per_mo": broker_base_usd_per_mo,
            "kms_base_usd_per_mo": kms_base_usd_per_mo,
            "hours_per_month": hours_per_month,
            "pricing_assumptions": [
                "GPU: $1.50/hr [ASSUMPTION: RunPod / Lambda 1x A10G spot, Oct 2026]",
                "CPU: $0.10/hr [ASSUMPTION: AWS c6g.large on-demand, Oct 2026]",
                "Broker: $150.00/mo [ASSUMPTION: AWS Managed Redis/Kafka base tier, Oct 2026]",
                "KMS: $50.00/mo [ASSUMPTION: AWS KMS CloudHSM tier, Oct 2026]"
            ]
        }

        payload = {
            "security_surface": "Zero-trust IAM with mTLS between worker pods; KMS enclave for blockchain key isolation",
            "cost_inputs": cost_inputs,
            "monthly_cost_estimate": {
                "pilot_tier_usd": pilot_cost,
                "scale_tier_usd": scale_cost
            },
            "kms_enclave_enabled": kms_enclave_enabled
        }
        contract = StageContract("STAGE_3_SECURITY_COST", "SecurityCostAgent", payload)
        await self.emit_contract(contract)
        return contract

    # --- Worker 4: Verification Judge Worker (Genuinely evaluates invariants) ---
    async def run_verification_judge_worker(self) -> StageContract:
        violations = []

        # 1. Check Discovery Stage Contract
        if "STAGE_1_DISCOVERY" not in self.state_ledger:
            violations.append("Missing STAGE_1_DISCOVERY contract in state ledger.")
        else:
            disc = self.state_ledger["STAGE_1_DISCOVERY"].payload
            if not disc.get("discovered_modules"):
                violations.append("Discovery failed: Zero modules identified.")

        # 2. Check Topology Stage Contract
        if "STAGE_2_DECOUPLING" not in self.state_ledger:
            violations.append("Missing STAGE_2_DECOUPLING contract in state ledger.")
        else:
            topo = self.state_ledger["STAGE_2_DECOUPLING"].payload
            if not topo.get("decoupling_verified"):
                if topo.get("decoupling_verified") is None:
                    violations.append("Topology unknown: decoupling_verified flag is not specified.")
                else:
                    violations.append("Topology failed: Asynchronous decoupling not verified.")

        # 3. Check Security Contract
        if "STAGE_3_SECURITY_COST" not in self.state_ledger:
            violations.append("Missing STAGE_3_SECURITY_COST contract in state ledger.")
        else:
            sec = self.state_ledger["STAGE_3_SECURITY_COST"].payload
            if not sec.get("kms_enclave_enabled"):
                if sec.get("kms_enclave_enabled") is None:
                    violations.append("Security unknown: kms_enclave_enabled flag is not specified.")
                else:
                    violations.append("Security violation: KMS enclave key isolation is disabled.")

        is_approved = (len(violations) == 0)
        payload = {
            "status": "APPROVED" if is_approved else "REJECTED",
            "violations": violations,
            "invariants_checked": 3,
            "synthesized_phases": [
                "Phase 1: Decouple inference queue from blockchain event listeners",
                "Phase 2: Introduce idempotent Redis state machine for transaction rollups",
                "Phase 3: Stress-test under synthetic burst loads"
            ] if is_approved else []
        }
        contract = StageContract("STAGE_4_SYNTHESIS", "VerificationJudgeAgent", payload)
        await self.emit_contract(contract)
        return contract

    async def execute_full_pipeline(self, system_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Spawns the background queue consumer, enqueues the initial discovery request,
        and awaits complete pipeline consumption through the queue.
        """
        self.audit_log.append(f"Starting decoupled event-driven pipeline for {self.system_name}...")
        
        # 1. Start real background queue consumer
        consumer_task = asyncio.create_task(self.queue_consumer_worker())

        # 2. Produce initial discovery contract to queue
        await self.run_discovery_worker(system_spec)

        # 3. Wait for consumer to process all stages through the queue
        await consumer_task

        judge_contract = self.state_ledger.get("STAGE_4_SYNTHESIS")
        status = judge_contract.payload["status"] if judge_contract else "UNKNOWN"

        return {
            "system_name": self.system_name,
            "overall_status": status,
            "contracts": {k: asdict(v) for k, v in self.state_ledger.items()},
            "audit_log": self.audit_log
        }
