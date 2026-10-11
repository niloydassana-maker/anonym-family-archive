"""
Generates video walkthrough for Namahatrix deliverable.
Builds 1080p architectural slides with dynamically captured stdout from real testbench executions.
"""

import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.path.join(BASE_DIR, "video_frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

def get_fonts():
    try:
        font_title = ImageFont.truetype("arial.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 24)
        font_heading = ImageFont.truetype("arial.ttf", 28)
        font_body = ImageFont.truetype("arial.ttf", 22)
        font_mono = ImageFont.truetype("consola.ttf", 18)
        font_foot = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_title = font_sub = font_heading = font_body = font_mono = font_foot = ImageFont.load_default()
    return font_title, font_sub, font_heading, font_body, font_mono, font_foot

def render_slide(title, subtitle, sections, footer, filename):
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)
    f_title, f_sub, f_head, f_body, f_mono, f_foot = get_fonts()

    # Header bar
    draw.rectangle([(0, 0), (1920, 140)], fill=(30, 41, 59))
    draw.text((80, 30), title, font=f_title, fill=(56, 189, 248))      # sky-400
    draw.text((80, 85), subtitle, font=f_sub, fill=(148, 163, 184))    # slate-400

    y = 170
    for sec_title, sec_content, is_code in sections:
        draw.text((80, y), sec_title, font=f_head, fill=(241, 245, 249))
        y += 36
        if is_code:
            box_lines = sec_content.strip().split("\n")
            box_height = len(box_lines) * 24 + 20
            draw.rectangle([(80, y), (1840, y + box_height)], fill=(2, 6, 23), outline=(51, 65, 85))
            cy = y + 10
            for line in box_lines:
                draw.text((105, cy), line, font=f_mono, fill=(167, 243, 208)) # emerald-200
                cy += 24
            y += box_height + 20
        else:
            for line in sec_content.strip().split("\n"):
                draw.text((100, y), line, font=f_body, fill=(203, 213, 225))
                y += 28
            y += 16

    # Footer bar
    draw.rectangle([(0, 1020), (1920, 1080)], fill=(30, 41, 59))
    draw.text((80, 1040), footer, font=f_foot, fill=(148, 163, 184))

    img.save(filename)

def build_namahatrix_video():
    print("\n--- Building Namahatrix Walkthrough Video from Captured Output ---")

    proc_demo = subprocess.run(
        ["python", "demo_runner.py"],
        cwd=os.path.join(BASE_DIR, "namahatrix"),
        capture_output=True, text=True, check=True
    )
    captured_demo_out = proc_demo.stdout.strip()

    proc_tests = subprocess.run(
        ["python", "-m", "unittest", "test_runtime.py"],
        cwd=os.path.join(BASE_DIR, "namahatrix"),
        capture_output=True, text=True
    )
    captured_test_summary = proc_tests.stderr.strip()

    slides = [
        # Slide 1: Title
        (
            "Namahatrix — Multi-Agent Architecture Testbed",
            "Event-Driven Architecture & Consumer Loop | Systems Architect: Kunal Das",
            [
                ("Executive Overview",
                 "• Architecture analysis of multi-agent pipelines interacting with blockchain states.\n"
                 "• Synchronous execution blocking: LLM generation blocking on blockchain block finality.\n"
                 "• Asynchronous queue buffer separating inference workers from state rollups.", False),
                ("Key Capabilities Demonstrated in Deliverable",
                 "1. Asynchronous queue message bus with dedicated background consumer worker.\n"
                 "2. Isolated worker contract boundaries across Discovery, Topology, Security, and Judge stages.\n"
                 "3. VerificationJudge evaluating architectural invariants (empty modules or insecure keys reject).", False)
            ],
            "Package: namahatrix/ | Recipient: Arjun Chowdhury",
            os.path.join(FRAMES_DIR, "n_slide1.png")
        ),
        # Slide 2: Target Architecture
        (
            "Namahatrix — Event-Driven Architecture",
            "Asynchronous Buffer vs Synchronous Blocking",
            [
                ("Architecture Blueprint",
                 "[ Multi-Agent Ingestion ] ──► [ Ray Inference Ring (vLLM / TensorRT) ]\n"
                 "                                     │ (Generated Actions)\n"
                 "                                     ▼\n"
                 "                          [ Redis Streams / Kafka Broker ]\n"
                 "                                     │ (Asynchronous Batch Queue)\n"
                 "                                     ▼\n"
                 "                    [ L2 Batch Rollup Worker (Arbitrum Orbit) ]\n"
                 "                                     │ (Optimistic Batch Settlement)\n"
                 "                                     ▼\n"
                 "                    [ Cryptographic State Settlement Ledger ]", True),
                ("Target Benefits [ESTIMATE / PROPOSAL]",
                 "• Separates inference queue from slow on-chain confirmation.\n"
                 "• Aggregates high-throughput agent state transitions into periodic batch proofs.", False)
            ],
            "Blueprint: ARCHITECTURE_ASSESSMENT_BLUEPRINT.md | Runtime: agent_decoupling_runtime.py",
            os.path.join(FRAMES_DIR, "n_slide2.png")
        ),
        # Slide 3: Runtime Implementation
        (
            "Namahatrix — Asynchronous Queue & Consumer Implementation",
            "Typed Stage Contracts & Real Background Queue Worker",
            [
                ("Runtime Code: agent_decoupling_runtime.py",
                 "class DecoupledAgentRuntime:\n"
                 "    def __init__(self, system_name):\n"
                 "        self.queue = asyncio.Queue()  # FIFO message queue\n"
                 "        self.state_ledger = {}         # State ledger populated by consumer\n"
                 "\n"
                 "    async def queue_consumer_worker(self):\n"
                 "        # Real background consumer draining contracts from queue\n"
                 "        while True:\n"
                 "            contract = await self.queue.get()\n"
                 "            self.state_ledger[contract.stage_id] = contract\n"
                 "            # Routes contract to downstream worker\n"
                 "            ...\n"
                 "            self.queue.task_done()", True),
                ("Verification Judge Invariants",
                 "Evaluates 3 invariants: non-empty modules, async buffer topology, and KMS enclave isolation.", False)
            ],
            "Verified by 7 automated unit tests in test_runtime.py",
            os.path.join(FRAMES_DIR, "n_slide3.png")
        ),
        # Slide 4: Real Captured Output
        (
            "Namahatrix — Captured Testbench Execution Logs",
            "Output captured when this video was built",
            [
                ("Captured Terminal Output (Raw Stdout)",
                 captured_demo_out, True),
                ("Unit Test Suite Status (Captured Stderr)",
                 captured_test_summary, True)
            ],
            "Output captured when this video was built: python demo_runner.py",
            os.path.join(FRAMES_DIR, "n_slide4.png")
        ),
        # Slide 5: Implementation Roadmap
        (
            "Namahatrix — Phase 1 Implementation Roadmap",
            "Phased Sprint Plan & Cost Modelling",
            [
                ("Phased Milestones [ESTIMATES]",
                 "• Sprint 1 (Days 1–5 [ESTIMATE]): Separate inference queue from RPC listeners; deploy Redis state machine.\n"
                 "• Sprint 2 (Days 6–10 [ESTIMATE]): Implement Arbitrum Orbit / Polygon CDK batch rollup workers.\n"
                 "• Sprint 3 (Days 11–14 [ESTIMATE]): End-to-end stress testing under synthetic burst workloads.\n"
                 "• Cost Formula: Broker + KMS + (GPU hrs * $1.50) + (CPU hrs * $0.10) [ASSUMPTION: rates, Oct 2026].\n"
                 "• Monthly Estimates: Pilot ~$420 - $1,200/mo [ESTIMATE] | Scale ~$4,500 - $14,200/mo [ESTIMATE].", False),
                ("Contact & Collaboration",
                 "Kunal Das | isearch.xsolve@gmail.com | WA: +91 86172 16163 | Systems Architect", False)
            ],
            "All numbers labeled as ESTIMATE or ASSUMPTION | Transparent cost modeling",
            os.path.join(FRAMES_DIR, "n_slide5.png")
        )
    ]

    for title, sub, secs, foot, fname in slides:
        render_slide(title, sub, secs, foot, fname)

    concat_txt = os.path.join(FRAMES_DIR, "concat_namahatrix.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for _, _, _, _, fname in slides:
            clean_fname = fname.replace("\\", "/")
            f.write(f"file '{clean_fname}'\n")
            f.write("duration 24\n")
        last_fname = slides[-1][4].replace("\\", "/")
        f.write(f"file '{last_fname}'\n")

    out_mp4 = os.path.join(BASE_DIR, "namahatrix", "namahatrix_architecture_walkthrough.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-r", "1", "-pix_fmt", "yuv420p",
        out_mp4
    ]
    subprocess.run(cmd, check=True)
    print(f"Namahatrix Walkthrough Video rebuilt: {out_mp4} (Size: {os.path.getsize(out_mp4)} bytes)")

if __name__ == "__main__":
    build_namahatrix_video()
