import os
import sys
import json
import py_compile
import subprocess
from pathlib import Path

VAULT_DIR = Path(r"D:\anonym\vault")
SCRATCH_DIR = Path(r"D:\anonym\scratch\kaggle_engines")
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Engine five intentionally shares the kunaldas3104 account but uses its fifth
# credential, giving the fleet five independently scheduled Kaggle kernels.
FLEET_ACCOUNTS = [
    {"engine": 1, "account": "isearchxsolve", "token_file": None},
    {"engine": 2, "account": "n42888", "token_file": VAULT_DIR / "kaggle_token_2.txt"},
    {"engine": 3, "account": "kunaldas3104", "token_file": VAULT_DIR / "kaggle_token_3.txt"},
    {"engine": 4, "account": "kdas19999", "token_file": VAULT_DIR / "kaggle_token_4.txt"},
    {"engine": 5, "account": "kunaldas3104", "token_file": VAULT_DIR / "kaggle_token_5.txt"},
]

def kaggle_environment(account: str, token_file: Path | None) -> tuple[dict | None, str | None]:
    """Return account-scoped Kaggle credentials without logging their values."""
    env = dict(os.environ)
    if token_file is None:
        return env, None
    if not token_file.exists():
        return None, f"token file missing: {token_file}"
    key = token_file.read_text(encoding="utf-8").strip()
    if not key:
        return None, f"token file is empty: {token_file}"
    if key.startswith("KGAT_"):
        env["KAGGLE_API_TOKEN"] = key
        env.pop("KAGGLE_USERNAME", None)
        env.pop("KAGGLE_KEY", None)
    else:
        env["KAGGLE_USERNAME"] = account
        env["KAGGLE_KEY"] = key
    return env, None


def deploy_all_engines() -> list[dict]:
    worker_src_path = Path(r"D:\anonym\scripts\kaggle_engine_worker.py")
    if not worker_src_path.exists():
        raise FileNotFoundError(f"Missing worker script: {worker_src_path}")
    worker_src = worker_src_path.read_text(encoding="utf-8")

    results = []
    for node in FLEET_ACCOUNTS:
        idx = node["engine"]
        account = node["account"]
        tok_file = node["token_file"]

        env, credential_error = kaggle_environment(account, tok_file)
        if credential_error:
            print(f"[FAILED] Engine {idx} ({account}): {credential_error}.")
            results.append({"engine": idx, "account": account, "success": False, "output": credential_error})
            continue

        engine_slug = f"bounty-engine-{idx}"
        engine_dir = SCRATCH_DIR / f"engine_{idx}"
        engine_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write worker.py with embedded ENGINE_ID (safely placed after __future__ import)
        engine_id_line = f'import os\nos.environ["ENGINE_ID"] = "{account}-{engine_slug}"\nos.environ["ENGINE_INDEX"] = "{idx}"\n'
        if "from __future__ import annotations" in worker_src:
            parts = worker_src.split("from __future__ import annotations", 1)
            worker_code = parts[0] + "from __future__ import annotations\n" + engine_id_line + parts[1]
        else:
            worker_code = engine_id_line + worker_src
        (engine_dir / "worker.py").write_text(worker_code, encoding="utf-8")
        try:
            py_compile.compile(str(engine_dir / "worker.py"), doraise=True)
        except py_compile.PyCompileError as exc:
            message = f"worker syntax validation failed: {exc.msg}"
            print(f"[FAILED] Engine {idx} ({account}): {message}")
            results.append({"engine": idx, "account": account, "success": False, "output": message})
            continue

        # 2. Write kernel-metadata.json
        meta = {
            "id": f"{account}/{engine_slug}",
            "title": f"Bounty Engine {idx}",
            "code_file": "worker.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_internet": True,
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": []
        }
        (engine_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        print(f"[Deploy] Pushing Engine {idx} ({engine_slug}) to Kaggle account '{account}'...")
        res = subprocess.run(
            [sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(engine_dir)],
            capture_output=True,
            text=True,
            env=env
        )
        out = (res.stdout or "") + (res.stderr or "")
        success = res.returncode == 0
        print(f" -> Result for Engine {idx}: {'OK (LIVE)' if success else 'FAILED: ' + out[:150]}")
        results.append({"engine": engine_slug, "account": account, "success": success, "output": out[:500]})

    return results

if __name__ == "__main__":
    deployment_results = deploy_all_engines()
    raise SystemExit(0 if deployment_results and all(row["success"] for row in deployment_results) else 1)
