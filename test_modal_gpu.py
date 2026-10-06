import sys
import os

# Force UTF-8 on Windows consoles so rich/modal unicode characters don't trigger charmap error
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import modal

app = modal.App("kilo-gpu-test")
image = modal.Image.debian_slim(python_version="3.11").pip_install("torch")

@app.function(gpu="l4", image=image)
def check_gpu():
    import torch
    device_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    return f"Modal L4 SUCCESS! Device: {device_name}, VRAM: {vram:.2f} GB"

@app.local_entrypoint()
def main():
    print("Connecting to Modal Cloud...")
    res = check_gpu.remote()
    print(">>> RESULT FROM MODAL CLOUD:", res)
