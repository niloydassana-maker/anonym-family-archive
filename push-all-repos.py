"""push-all-repos.py — sweep nested/outer project folders, commit and push each as its own private repo.

Rules:
- IF EXISTING repo (has .git + remote): git add -A, commit (if changes), push.
- IF folder is a project but has no .git: git init, create private GitHub repo via gh, push.
- Skips: node_modules, venvs, backups, archives, chrome-profiles, junk (configurable).
- Does NOT touch D:\anonym (this workspace's own work area) or system dirs.
"""
import os, subprocess, sys, json

DRIVES = [r"D:\god_ai", r"D:\emergentsh_latest", r"D:\neon_unified", r"D:\omniroute-monetizer",
          r"D:\nemo_test", r"D:\codex-nvidia-proxy", r"D:\dev", r"D:\DOWNLOADS", r"D:\gpt_terra"]

SKIP_DIRS = {"node_modules", ".venv", "venv", "env", "__pycache__", "chrome-profile",
             "BACKUP", "_BACKUP", "backup", "archives", "archive", "life_archive",
             "LIFE_ARCHIVE", "99_PRIVATE", ".next", "dist", "build", "coverage", "htmlcov",
             "emergentsh_old", "emergentsh-standalone_old", "lasthelp", "preview_apps",
             "live_generated_expo-node", "live_generated_fastapi-react", "live_generated_flutter-fastapi",
             "live_generated_nextjs-postgres", "test_sdlc_sandbox", "oioi"}

MAX_SIZE_MB = 800  # skip repos whose working tree exceeds this (no LFS today)

def run(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="ignore")
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def dir_size_mb(path):
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".git")]
        for f in files:
            try: total += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    return total / 1024 / 1024

def is_project(path):
    if not os.path.isdir(path): return False
    entries = set(os.listdir(path))
    markers = {"package.json", "pyproject.toml", "requirements.txt", "README.md",
               "setup.py", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
               "pubspec.yaml", "compose.yaml", "docker-compose.yml", "src", "app", "server", "docs"}
    return bool(entries & markers) and os.path.basename(path) not in SKIP_DIRS

def ensure_private_remote(path, name):
    # create private repo if missing
    code, out = run(["gh", "repo", "view", f"isearchxsolve/{name}", "--json", "name"], path, check=False)
    if code == 0:
        return f"isearchxsolve/{name} (exists)"
    code, out = run(["gh", "repo", "create", f"isearchxsolve/{name}", "--private", "--confirm"], path, check=False)
    return f"isearchxsolve/{name} (created)" if code == 0 else f"create-failed: {out[:120]}"

def sanitize(name):
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in name).strip("-").lower()

results = []

def process_repo(path, label):
    name = sanitize(label)[:80]
    gitdir = os.path.join(path, ".git")
    size = dir_size_mb(path)
    if size > MAX_SIZE_MB and not os.path.exists(gitdir):
        results.append({"repo": label, "status": "SKIPPED (too large, no git)", "size_mb": round(size)})
        return
    if not os.path.exists(gitdir):
        run(["git", "init", "-b", "main"], path)
        # safety: ignore heavy junk
        gi = os.path.join(path, ".gitignore")
        if not os.path.exists(gi):
            with open(gi, "w") as f:
                f.write("node_modules/\nvenv/\n.venv/\n__pycache__/\n*.log\n.env\n*.key\n*.pem\ndist/\nbuild/\ncoverage/\n.next/\n")
        remote = ensure_private_remote(path, name)
        run(["git", "remote", "add", "origin", f"https://github.com/isearchxsolve/{name}.git"], path)
    else:
        code, out = run(["git", "remote", "get-url", "origin"], path, check=False)
        if code != 0 or "github.com" not in out:
            remote = ensure_private_remote(path, name)
            if "create-failed" not in remote:
                run(["git", "remote", "remove", "origin"], path)
                run(["git", "remote", "add", "origin", f"https://github.com/isearchxsolve/{name}.git"], path)
    run(["git", "add", "-A"], path)
    code, out = run(["git", "commit", "-m", "Chore: sync workspace state 2026-09-06"], path, check=False)
    committed = code == 0
    branch = "main"
    cb, out = run(["git", "branch", "--show-current"], path, check=False)
    if cb == 0 and out.strip(): branch = out.strip()
    code, out = run(["git", "push", "-u", "origin", branch], path, check=False)
    pushed = code == 0
    results.append({"repo": label, "path": path, "size_mb": round(size),
                    "committed": committed, "pushed": pushed,
                    "detail": out.strip().splitlines()[-1][:100] if out.strip() else ""})

def walk_for_projects(root, depth=0, label_prefix=""):
    if depth > 2: return
    try: entries = os.listdir(root)
    except OSError: return
    for e in entries:
        if e in SKIP_DIRS or e.startswith("."): continue
        p = os.path.join(root, e)
        if not os.path.isdir(p): continue
        if os.path.exists(os.path.join(p, ".git")) or is_project(p):
            process_repo(p, (label_prefix + e)[:90])
            # do not descend into repos (their subfolders are part of the repo)
        else:
            walk_for_projects(p, depth + 1, label_prefix + e + "/")

for drive in DRIVES:
    if not os.path.isdir(drive): continue
    if os.path.exists(os.path.join(drive, ".git")) or is_project(drive):
        process_repo(drive, os.path.basename(drive.rstrip("\\/")) or drive)
    walk_for_projects(drive, 0)

print(json.dumps(results, indent=1))
with open(r"D:\anonym\career\push-all-report.json", "w") as f:
    json.dump(results, f, indent=1)
