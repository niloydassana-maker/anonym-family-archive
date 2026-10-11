"""
Namahatrix - Multi-Agent Runtime Live Demonstration Runner
Runs the decoupled multi-agent pipeline and outputs verified ledger state.
"""

import asyncio
import json
from agent_decoupling_runtime import DecoupledAgentRuntime

def run_demo():
    print("=" * 70)
    print(" NAMAHATRIX: ASYNCHRONOUS DECOUPLED MULTI-AGENT RUNTIME TESTBENCH")
    print(" Systems Architecture Validation")
    print("=" * 70)

    runtime = DecoupledAgentRuntime(system_name="Namahatrix Core Architecture")

    spec = {
        "modules": ["Cloud-Ingestion", "AI-Inference-Layer", "Blockchain-State-Anchor"],
        "peak_tps": 15000,
        "bottleneck": "Tightly coupled synchronous LLM blocking on blockchain state confirmations",
        "kms_enclave_enabled": True,
        "decoupling_verified": True
    }

    print("\n[1] Dispatching Pipeline Stages via Asynchronous Queue...")
    summary = asyncio.run(runtime.execute_full_pipeline(spec))

    for log in summary["audit_log"]:
        print(f"     {log}")

    # Cost Model Outputs (Continuous Formula, No Cliffs)
    stage_3 = summary["contracts"]["STAGE_3_SECURITY_COST"]["payload"]
    costs = stage_3["monthly_cost_estimate"]
    inputs = stage_3["cost_inputs"]
    print("\n[2] Cost Model Evaluation (Continuous Formula, No Cliffs):")
    print("     Named Pricing Inputs:")
    for a in inputs["pricing_assumptions"]:
        print(f"       * {a}")
    print(f"     Monthly Cost Estimates at {spec['peak_tps']} peak TPS [ESTIMATE]:")
    print(f"       * Pilot Tier: ${costs['pilot_tier_usd']:.2f}/mo [ESTIMATE]")
    print(f"       * Scale Tier: ${costs['scale_tier_usd']:.2f}/mo [ESTIMATE]")

    print("\n[3] Verification Judge Verdict:")
    stage_4 = summary["contracts"]["STAGE_4_SYNTHESIS"]["payload"]
    print(f"     Status: {stage_4['status']}")
    print(f"     Invariants Evaluated: {stage_4['invariants_checked']}")
    print(f"     Violations Found: {len(stage_4['violations'])}")
    if stage_4["synthesized_phases"]:
        print("     Approved Execution Phases:")
        for p in stage_4["synthesized_phases"]:
            print(f"       * {p}")

    print("\n" + "=" * 70)
    if stage_4["status"] == "APPROVED":
        print(" PIPELINE EXECUTION APPROVED")
    else:
        print(f" PIPELINE EXECUTION {stage_4['status']}")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
