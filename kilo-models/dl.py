import os
import sys
import time

import requests
from kaggle import api
from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest

OWNER, KERNEL = "kkk3213", "kilo-xtts-tune"
TARGETS = ["father_last.pth", "config.json"]
OUT = r"D:\anonym\kilo-models"
os.makedirs(OUT, exist_ok=True)
LOGF = open(OUT + r"\dl.log", "a", encoding="utf-8")


def log(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    LOGF.write(line + "\n")
    LOGF.flush()


def list_files():
    token = None
    all_files = []
    with api.build_kaggle_client() as kaggle:
        while True:
            req = ApiListKernelSessionOutputRequest()
            req.user_name = OWNER
            req.kernel_slug = KERNEL
            req.page_size = 200
            if token:
                req.page_token = token
            resp = kaggle.kernels.kernels_api_client.list_kernel_session_output(req)
            all_files.extend(resp.files or [])
            token = resp.next_page_token
            log(f"listed {len(all_files)} so far, next={'y' if token else 'n'}")
            if not token:
                return all_files


def download(url, dest):
    tmp = dest + ".part"
    pos = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    headers = {"Range": f"bytes={pos}-"} if pos else {}
    r = requests.get(url, stream=True, headers=headers, timeout=120)
    if r.status_code not in (200, 206):
        raise RuntimeError(f"HTTP {r.status_code}")
    mode = "ab" if r.status_code == 206 else "wb"
    total = pos + int(r.headers.get("content-length", 0))
    last = 0
    with open(tmp, mode) as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
            if f.tell() - last > (100 << 20):
                last = f.tell()
                mb_done = last / (1 << 20)
                mb_total = total / (1 << 20)
                log(f"{os.path.basename(dest)}: {mb_done:.0f}MB / {mb_total:.0f}MB")
    os.replace(tmp, dest)
    done_mb = os.path.getsize(dest) / (1 << 20)
    log(f"DONE {os.path.basename(dest)} {done_mb:.1f}MB")


files = list_files()
by_name = {}
for it in files:
    for t in TARGETS:
        if it.file_name.endswith("/" + t) or it.file_name == t:
            by_name[t] = it
for t in TARGETS:
    it = by_name.get(t)
    if not it:
        log(f"MISSING {t} (have {len(files)} files)")
        continue
    dest = os.path.join(OUT, t)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        log(f"SKIP {t} already present")
        continue
    for attempt in range(6):
        try:
            download(it.url, dest)
            break
        except Exception as e:
            log(f"retry {t} #{attempt}: {type(e).__name__} {str(e)[:120]}")
            time.sleep(10)
log("ALL-DONE")
