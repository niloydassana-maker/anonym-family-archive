import sys
import os
import time

# Force UTF-8 on Windows consoles
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import modal

app = modal.App("kilo-xtts-l4-bench")

# Build image with PyTorch and Coqui-TTS
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "torch",
        "torchaudio",
        "torchcodec",
        "transformers<4.44",
        "click",
        "coqui-tts",
        "scipy",
        "numpy",
    )
)

@app.function(gpu="l4", image=image, timeout=600)
def benchmark_xtts_l4(ref_wav_bytes: bytes, test_text: str):
    import torch
    import time
    from TTS.api import TTS

    print("--- [L4 WORKER] Hardware Check ---")
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"GPU: {gpu_name} | VRAM: {vram:.2f} GB")

    # Save reference wav locally
    ref_path = "/tmp/clinic_reference.wav"
    with open(ref_path, "wb") as f:
        f.write(ref_wav_bytes)

    os.environ["COQUI_TOS_AGREED"] = "1"
    print("--- [L4 WORKER] Loading XTTS-v2 Model ---")
    t_load0 = time.time()
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to("cuda")
    t_load = time.time() - t_load0
    print(f"XTTS Model Loaded in {t_load:.2f}s")

    # Warm-up run
    print("--- [L4 WORKER] Warm-up run ---")
    tts.tts_to_file(
        text="नमस्ते।",
        speaker_wav=ref_path,
        language="hi",
        file_path="/tmp/warmup.wav",
        speed=1.35
    )

    # Benchmark test run
    print(f"--- [L4 WORKER] Benchmarking Inference: '{test_text}' ---")
    out_path = "/tmp/bench_out.wav"
    t_gen0 = time.time()
    tts.tts_to_file(
        text=test_text,
        speaker_wav=ref_path,
        language="hi",
        file_path=out_path,
        speed=1.35
    )
    t_gen = time.time() - t_gen0

    # Read generated wav
    with open(out_path, "rb") as f:
        out_wav = f.read()

    # Calculate audio duration
    import wave
    with wave.open(out_path, "rb") as wf:
        nframes = wf.getnframes()
        rate = wf.getframerate()
        duration_s = nframes / float(rate)

    rtf = t_gen / duration_s if duration_s > 0 else 0
    print(f"--- [L4 BENCHMARK RESULTS] ---")
    print(f"Inference Time: {t_gen*1000:.1f} ms")
    print(f"Audio Duration: {duration_s:.2f} s")
    print(f"Real-Time Factor (RTF): {rtf:.3f}")

    return {
        "gpu": gpu_name,
        "vram_gb": vram,
        "inference_ms": round(t_gen * 1000, 1),
        "duration_s": round(duration_s, 2),
        "rtf": round(rtf, 3),
        "wav_bytes": out_wav
    }

@app.local_entrypoint()
def main():
    ref_file = r"D:\anonym\RESCUE-kaggle-reset\dataset-pull\clinic_reference.wav"
    if not os.path.exists(ref_file):
        # Fallback check
        ref_file = r"D:\anonym\realhindivoice\reference_clean.wav"
    print(f"Loading reference voice from: {ref_file}")
    with open(ref_file, "rb") as f:
        ref_bytes = f.read()

    test_sentence = "नमस्ते, सुगर डॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या मदद कर सकता हूँ?"
    print(f"Sending request to Modal NVIDIA L4...")
    result = benchmark_xtts_l4.remote(ref_bytes, test_sentence)

    print("\n==========================================")
    print("  MODAL NVIDIA L4 XTTS BENCHMARK RESULTS  ")
    print("==========================================")
    print(f"GPU Hardware:    {result['gpu']} ({result['vram_gb']:.1f} GB)")
    print(f"Audio Duration:  {result['duration_s']} seconds")
    print(f"Inference Time:  {result['inference_ms']} ms")
    print(f"RTF:             {result['rtf']}")
    print("==========================================")

    # Save local wav for listening verification
    out_file = r"D:\anonym\l4_benchmark_output.wav"
    with open(out_file, "wb") as f:
        f.write(result["wav_bytes"])
    print(f"Saved benchmark audio to: {out_file}")
