# _wire_opencode.py — idempotent opencode config surgery for kilo-bridge-setup.ps1.
# Usage:  python _wire_opencode.py <config_path> <node_exe> <mcp_index_js> <model_id>
# The NVIDIA key is passed via env WIRE_NVKEY (never on the argv line).
# Prints CHANGED <fields> / UNCHANGED / ABORT_HAS_COMMENTS. ASCII only.
import json
import os
import re
import sys

path, node_exe, mcp_index, model_id = sys.argv[1:5]
key = os.environ.get("WIRE_NVKEY", "")

raw = open(path, encoding="utf-8").read()
if re.search(r"(?m)^\s*//", raw):
    print("ABORT_HAS_COMMENTS")
    sys.exit(2)
cfg = json.loads(raw)
changed = []

mcp = cfg.setdefault("mcp", {})
want_cmd = [node_exe, mcp_index]
cur = mcp.get("browser-mcp") or {}
if cur.get("type") != "local" or cur.get("command") != want_cmd or cur.get("enabled") is not True:
    mcp["browser-mcp"] = {"type": "local", "command": want_cmd, "enabled": True}
    changed.append("mcp.browser-mcp")
cd = mcp.get("chrome-devtools")
if not isinstance(cd, dict):
    mcp["chrome-devtools"] = {"type": "local",
                              "command": ["npx", "-y", "chrome-devtools-mcp@latest"],
                              "enabled": False}
    changed.append("mcp.chrome-devtools.added-disabled")
elif cd.get("enabled") is not False:
    cd["enabled"] = False
    changed.append("mcp.chrome-devtools.disabled")
if cfg.get("model") != model_id:
    cfg["model"] = model_id
    changed.append("model")
agt = cfg.get("agent", {}).get("build")
if isinstance(agt, dict) and agt.get("model") != model_id:
    agt["model"] = model_id
    changed.append("agent.build.model")
if key:
    prov = cfg.setdefault("provider", {}).setdefault("nvidia", {})
    opts = prov.setdefault("options", {})
    if opts.get("apiKey") != key:
        opts["apiKey"] = key
        changed.append("provider.nvidia.apiKey")
    prov.setdefault("npm", "@ai-sdk/openai-compatible")
    prov.setdefault("name", "NVIDIA NIM Free Endpoints")
    opts.setdefault("baseURL", "https://integrate.api.nvidia.com/v1")
    m550 = prov.setdefault("models", {}).setdefault("nvidia/nemotron-3-ultra-550b-a55b", {})
    if m550.get("tool_call") is not True:
        m550.update({"name": "NIM Nemotron 3 Ultra 550B",
                     "attachment": False, "tool_call": True, "reasoning": False,
                     "modalities": {"input": ["text"], "output": ["text"]},
                     "limit": {"context": 1000000, "output": 8192}})
        changed.append("provider.nvidia.models.550b")

if changed:
    open(path, "w", encoding="utf-8").write(json.dumps(cfg, indent=2) + "\n")
print("CHANGED " + ",".join(changed) if changed else "UNCHANGED")
