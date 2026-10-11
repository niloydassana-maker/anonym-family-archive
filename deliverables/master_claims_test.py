#!/usr/bin/env python3
"""
MASTER CLAIMS TEST  -  "is every claim in this package earned?"

Stdlib only. Windows/Linux/macOS. Run from anywhere:

    python master_claims_test.py --root D:\anonym\deliverables
    python master_claims_test.py --root . --video-label slides
    python master_claims_test.py --capture-live         # needs LTA_DATAMALL_KEY, creates live proof
    python master_claims_test.py --write-receipt        # writes evidence/RUN_RECEIPT.* from THIS run

Layout expected under --root:   transportlah/   namahatrix/   (+ any *.md, *.txt, *.mp4)

Design rules (why this script can be trusted more than a demo):
  1. Every check CAN fail. Exit code is 1 if any check is FAIL.
  2. Behavior is tested by running code with inputs that should be rejected.
  3. The package's own unit tests are tested too (mutation testing): code is
     deliberately broken, and the tests MUST notice. A survivor = a test that proves nothing.
  4. Every claim phrase found in docs/video-script must be backed by evidence
     (code, a test result, or a captured file). No evidence = FAIL.
  5. Receipts older than the code, or with no exit codes, are FAIL.
  6. Statuses:  PASS | FAIL | WARN | KNOWN (limit disclosed in docs) | SKIP | INFO
"""
import argparse, asyncio, glob, hashlib, importlib, json, os, platform, random
import re, shutil, subprocess, sys, tempfile, time, traceback
import urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ARGS = None
ROOT = None
RESULTS = []          # dicts: id, status, claim, evidence
CHECKS = []           # (id, claim, fn)


# ----------------------------------------------------------------- harness
def check(cid, claim):
    def deco(fn):
        CHECKS.append((cid, claim, fn))
        return fn
    return deco


def status_of(cid):
    for r in RESULTS:
        if r["id"] == cid:
            return r["status"]
    return None


def emit(cid, status, claim, evidence=""):
    RESULTS.append({"id": cid, "status": status, "claim": claim, "evidence": str(evidence)})
    print("[%-5s] %-4s %s" % (status, cid, claim))
    for line in str(evidence).splitlines():
        print("           " + line)


def run_all():
    for cid, claim, fn in CHECKS:
        try:
            status, evidence = fn()
        except Exception:
            status, evidence = "FAIL", "EXCEPTION (check could not run):\n" + traceback.format_exc(limit=3)
        emit(cid, status, claim, evidence)


def load(pkg, mod):
    path = os.path.join(ROOT, pkg)
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(mod)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def walk_files(exts=None):
    out = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", ".git", "video_frames")]
        for fn in files:
            if exts is None or fn.lower().endswith(exts):
                out.append(os.path.join(d, fn))
    return out


def is_self(path):
    return os.path.abspath(path) == os.path.abspath(__file__)


# ----------------------------------------------------------------- fixtures
BASE = datetime(2026, 10, 10, 23, 55, 0, tzinfo=timezone.utc)
BUS_PTS = [(1.3048, 103.8318, 0), (1.3015, 103.8385, 180), (1.2990, 103.8450, 360)]
M_PER_DEG = 111194.93  # 1 degree of latitude on a 6371 km sphere


def iso(sec, z=True):
    d = BASE + timedelta(seconds=sec)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ" if z else "%Y-%m-%dT%H:%M:%S")


def bus():
    return [{"lat": a, "lng": b, "timestamp": iso(t)} for a, b, t in BUS_PTS]


def ride(dlat_m=0.0, dt=0, z=True):
    return [{"lat": a + dlat_m / M_PER_DEG, "lng": b, "timestamp": iso(t + dt, z)} for a, b, t in BUS_PTS]


def verify(commuter, **kw):
    tv = load("transportlah", "spatial_verification")
    kw.setdefault("max_distance_threshold_m", 100.0)
    kw.setdefault("max_time_drift_sec", 30.0)
    return tv.SpatialVerificationEngine.verify_transit_segment(commuter, bus(), **kw)


def known_limit_disclosed(word_regex):
    for p in walk_files((".md", ".txt")):
        if is_self(p):
            continue
        t = read_text(p)
        if "KNOWN LIMIT" in t and re.search(word_regex, t, re.I):
            return p
    return None


# ================================================== A. TRANSPORTLAH behavior
@check("B0", "Haversine matches an independent oracle (1 deg latitude = 111,194.9 m, +-1 m)")
def b0():
    tv = load("transportlah", "spatial_verification")
    h = tv.SpatialVerificationEngine.haversine_distance
    d1, d2, z = h((0.0, 0.0), (1.0, 0.0)), h((0.0, 0.0), (0.0, 1.0)), h((1.3, 103.8), (1.3, 103.8))
    ok = abs(d1 - M_PER_DEG) < 1 and abs(d2 - M_PER_DEG) < 1 and z == 0
    return ("PASS" if ok else "FAIL"), "lat=%.2f lon=%.2f same-point=%s (expected ~%.2f)" % (d1, d2, z, M_PER_DEG)


@check("B1", "A genuine ride (in place, in time, jitter ~30 m) is verified 3/3")
def b1():
    r = verify(ride(dlat_m=30, dt=4))
    return ("PASS" if r["verified"] and r["matched_pings"] == 3 else "FAIL"), json.dumps(r)[:300]


@check("B2", "Right places, WRONG TIME (+12 h) is rejected")
def b2():
    r = verify(ride(dt=12 * 3600))
    return ("PASS" if not r["verified"] else "FAIL"), "verified=%s" % r["verified"]


@check("B3", "Wrong place (London) is rejected")
def b3():
    r = verify([{"lat": 51.5074, "lng": -0.1278, "timestamp": iso(0)}] * 3)
    return ("PASS" if not r["verified"] else "FAIL"), "verified=%s" % r["verified"]


@check("B4", "Person who never moved (3 pings at stop 1, bus times) is rejected")
def b4():
    c = [{"lat": 1.3049, "lng": 103.8319, "timestamp": iso(t)} for _, _, t in BUS_PTS]
    r = verify(c)
    return ("PASS" if not r["verified"] else "FAIL"), "verified=%s ratio=%s" % (r["verified"], r.get("match_ratio"))


@check("B5", "Route in REVERSE order (right places, times ascending) is rejected")
def b5():
    c = [{"lat": BUS_PTS[2 - i][0], "lng": BUS_PTS[2 - i][1], "timestamp": iso(BUS_PTS[i][2])} for i in range(3)]
    r = verify(c)
    return ("PASS" if not r["verified"] else "FAIL"), "verified=%s" % r["verified"]


@check("B6", "Spatial threshold is exact: 50 m passes, 150 m fails (limit 100 m)")
def b6():
    a, b = verify(ride(dlat_m=50))["verified"], verify(ride(dlat_m=150))["verified"]
    return ("PASS" if a and not b else "FAIL"), "50m->%s  150m->%s" % (a, b)


@check("B7", "Time window is exact: +25 s passes, +35 s fails (limit 30 s)")
def b7():
    a, b = verify(ride(dt=25))["verified"], verify(ride(dt=35))["verified"]
    return ("PASS" if a and not b else "FAIL"), "+25s->%s  +35s->%s" % (a, b)


@check("B8", "A one-ping 'ride' must NOT verify (start+end cannot be shown by one ping)")
def b8():
    r = verify([ride()[0]])
    return ("PASS" if not r["verified"] else "FAIL"), "verified=%s (single ping)" % r["verified"]


@check("B9", "Replay of the bus's own public coordinates+times (spoof) is rejected")
def b9():
    r = verify(bus())
    if not r["verified"]:
        return "PASS", "spoof rejected"
    p = known_limit_disclosed(r"replay|spoof")
    if p:
        return "KNOWN", "spoof ACCEPTED, but limit is disclosed in %s" % os.path.basename(p)
    return "FAIL", ("spoof ACCEPTED and not disclosed. Add a 'KNOWN LIMIT: replay/spoof ...' line to the README "
                    "or fix it. Do NOT claim spoof rejection.")


@check("B10", "Same wall-clock time gives the same verdict with or without a 'Z' (timezone safety)")
def b10():
    tl = os.path.join(ROOT, "transportlah")
    child = (
        "import sys; sys.path.insert(0, %r)\n"
        "from spatial_verification import SpatialVerificationEngine as S\n"
        "bus=[{'lat':1.3048,'lng':103.8318,'timestamp':'2026-10-10T23:55:00Z'}]\n"
        "c=[{'lat':1.3049,'lng':103.8319,'timestamp':'2026-10-10T23:55:04'}]\n"
        "print(S.verify_transit_segment(c,bus,max_distance_threshold_m=100.0,max_time_drift_sec=30.0)['verified'])\n"
    ) % tl
    if os.name == "posix":
        outs = {}
        for tz in ("UTC", "Asia/Kolkata", "Asia/Singapore", "America/New_York"):
            env = dict(os.environ, TZ=tz)
            outs[tz] = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, env=env).stdout.strip()
        ok = len(set(outs.values())) == 1
        return ("PASS" if ok else "FAIL"), "verdict by machine timezone: %s" % outs
    if time.timezone == 0:
        return "WARN", "this machine is on UTC, so the bug cannot show here. Re-run on a non-UTC machine."
    z, n = verify(ride(dt=4, z=True))["verified"], verify(ride(dt=4, z=False))["verified"]
    return ("PASS" if z == n else "FAIL"), "with Z=%s  naive=%s  (machine tz offset %ss)" % (z, n, -time.timezone)


@check("B11", "Garbage input fails safe (missing timestamp, NaN latitude) - no crash, no approval")
def b11():
    out = []
    for name, c in (("missing-ts", [{"lat": 1.3, "lng": 103.8}] * 3),
                    ("nan-lat", [{"lat": float("nan"), "lng": 103.8, "timestamp": iso(0)}] * 3)):
        try:
            out.append((name, verify(c)["verified"]))
        except Exception as e:
            out.append((name, "CRASH:%s" % type(e).__name__))
    ok = all(v is False for _, v in out)
    return ("PASS" if ok else "FAIL"), str(out)


# ================================================== B. LTA PROXY behavior
class _Resp:
    def __init__(self, payload):
        self._p = payload
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(self._p).encode()


def _with_fake_urlopen(fn):
    real, calls = urllib.request.urlopen, []
    def fake(req, timeout=None):
        calls.append(getattr(req, "full_url", str(req)))
        return _Resp({"odata.metadata": "x", "BusStopCode": "00000", "Services": []})
    urllib.request.urlopen = fake
    try:
        return fn(calls)
    finally:
        urllib.request.urlopen = real


@check("C1", "Offline mode labels its data OFFLINE_FIXTURE; unknown stops return an error, not invented data")
def c1():
    lp = load("transportlah", "lta_datamall_proxy")
    p = lp.LTADataMallProxy()
    p.api_key, p.mode = None, "OFFLINE_FIXTURE"
    known, unknown = p.get_bus_arrival("09048", "190"), p.get_bus_arrival("99999", "1")
    ok = known.get("_source") == "OFFLINE_FIXTURE" and unknown.get("error") is True and not unknown.get("Services")
    return ("PASS" if ok else "FAIL"), "known._source=%s  unknown.error=%s" % (known.get("_source"), unknown.get("error"))


@check("C2", "TTL cache really prevents repeat network calls (2 calls inside TTL -> 1 request; after TTL -> 2)")
def c2():
    lp = load("transportlah", "lta_datamall_proxy")
    def go(calls):
        p = lp.LTADataMallProxy(api_key="TESTKEY", cache_ttl_sec=0.3)
        p.get_bus_arrival("09048", "190"); p.get_bus_arrival("09048", "190")
        inside = len(calls)
        time.sleep(0.45)
        p.get_bus_arrival("09048", "190")
        return inside, len(calls)
    inside, after = _with_fake_urlopen(go)
    return ("PASS" if (inside, after) == (1, 2) else "FAIL"), "requests inside TTL=%s, after expiry=%s (want 1 then 2)" % (inside, after)


@check("C3", "A network failure is reported as an error and NEVER replaced by fixture data")
def c3():
    lp = load("transportlah", "lta_datamall_proxy")
    real = urllib.request.urlopen
    def boom(req, timeout=None):
        raise urllib.error.URLError("simulated outage")
    urllib.request.urlopen = boom
    try:
        r = lp.LTADataMallProxy(api_key="TESTKEY").get_bus_arrival("09048", "190")
    finally:
        urllib.request.urlopen = real
    ok = r.get("error") is True and not r.get("Services") and "ERROR" in str(r.get("_source"))
    return ("PASS" if ok else "FAIL"), "error=%s source=%s services=%s" % (r.get("error"), r.get("_source"), r.get("Services"))


@check("C4", "Live request goes to an https, versioned (v3) BusArrival URL  [from third-party sources; confirm in LTA guide]")
def c4():
    lp = load("transportlah", "lta_datamall_proxy")
    def go(calls):
        lp.LTADataMallProxy(api_key="TESTKEY").get_bus_arrival("09048", "190")
        return calls[0] if calls else ""
    url = _with_fake_urlopen(go)
    ok = url.startswith("https://") and "/v3/" in url
    return ("PASS" if ok else "WARN"), "URL used: %s" % url


EVID = lambda *p: os.path.join(ROOT, "evidence", *p)


@check("C5", "LIVE proof exists: a captured, recent, untouched response from the real LTA API")
def c5():
    path = EVID("lta_live_capture.json")
    if not os.path.exists(path):
        return "WARN", "no evidence/lta_live_capture.json. Run with --capture-live and a real key. Until then never write 'live' or 'real-time'."
    d = json.load(open(path, encoding="utf-8"))
    age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(d["captured_at_utc"])).total_seconds() / 3600
    raw_ok = isinstance(d.get("raw"), dict) and "Services" in d["raw"] and d.get("source") == "LIVE_NETWORK"
    hash_ok = hashlib.sha256(json.dumps(d.get("raw"), sort_keys=True).encode()).hexdigest() == d.get("raw_sha256")
    ok = raw_ok and hash_ok and age_h <= ARGS.max_age_hours
    return ("PASS" if ok else "FAIL"), "source=%s hash_ok=%s age=%.1fh (max %sh)" % (d.get("source"), hash_ok, age_h, ARGS.max_age_hours)


# ================================================== C. NAMAHATRIX behavior
def _run(spec, name="T"):
    m = load("namahatrix", "agent_decoupling_runtime")
    rt = m.DecoupledAgentRuntime(name)
    res = asyncio.run(rt.execute_full_pipeline(spec))
    return rt, res


LOW = {"modules": ["A"], "peak_tps": 100, "bottleneck": "none"}
HIGH = {"modules": ["A", "B", "C"], "peak_tps": 50000, "bottleneck": "synchronous blocking"}


@check("D1", "Pipeline output depends on INPUT (low-load spec and high-load spec give different topology)")
def d1():
    _, a = _run(LOW)
    _, b = _run(HIGH)
    ta, tb = a["contracts"]["STAGE_2_DECOUPLING"]["payload"], b["contracts"]["STAGE_2_DECOUPLING"]["payload"]
    return ("PASS" if ta != tb else "FAIL"), "low=%s | high=%s" % (ta.get("buffer_architecture"), tb.get("buffer_architecture"))


@check("D2", "The Judge can reject for reasons OTHER than 'empty input' when run through the real pipeline (fuzz, 300 specs)")
def d2():
    rnd, reasons, approved = random.Random(7), set(), 0
    for _ in range(300):
        spec = {"modules": ["m%d" % i for i in range(rnd.randint(1, 4))],
                "peak_tps": rnd.choice([0, 10, 5000, 15000, 10 ** 6]),
                "bottleneck": rnd.choice(["none", "synchronous", "Synchronous LLM blocking"]),
                "kms_enclave_enabled": rnd.choice([True, False]), "decoupling_verified": rnd.choice([True, False]),
                "tls": rnd.choice([True, False]), "security": {"kms": rnd.choice([True, False])}}
        _, res = _run(spec)
        if res["overall_status"] == "APPROVED":
            approved += 1
        else:
            for v in res["contracts"]["STAGE_4_SYNTHESIS"]["payload"].get("violations", []):
                reasons.add(v)
    ok = len(reasons) > 0
    return ("PASS" if ok else "FAIL"), "approved %d/300; distinct rejection reasons: %s" % (approved, sorted(reasons) or "NONE (judge cannot fail on non-empty input)")


@check("D3", "Queue is actually consumed (producer/consumer decoupling): queue is empty after the run")
def d3():
    rt, _ = _run(HIGH)
    n = rt.queue.qsize()
    return ("PASS" if n == 0 else "FAIL"), "%d unconsumed items left in the queue (items are put() but never get())" % n


@check("D4", "Cost estimate responds to load (50k TPS must not cost the same as 100 TPS)")
def d4():
    _, a = _run(LOW)
    _, b = _run(HIGH)
    ca, cb = a["contracts"]["STAGE_3_SECURITY_COST"]["payload"]["monthly_cost_estimate"], b["contracts"]["STAGE_3_SECURITY_COST"]["payload"]["monthly_cost_estimate"]
    return ("PASS" if ca != cb else "FAIL"), "low=%s high=%s" % (ca, cb)


@check("D5", "Deterministic: same input x10 gives identical output (timestamps stripped)")
def d5():
    def norm(res):
        s = json.dumps(res["contracts"], sort_keys=True, default=str)
        s = re.sub(r'"timestamp": [0-9.]+', '"timestamp": 0', s)
        return s
    outs = {norm(_run(HIGH)[1]) for _ in range(10)}
    return ("PASS" if len(outs) == 1 else "FAIL"), "%d distinct outputs" % len(outs)


# ================================================== D. Do the package's OWN tests mean anything?
def _unit_tests(pkg):
    d = os.path.join(ROOT, pkg)
    r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=d, capture_output=True, text=True, timeout=180)
    return r.returncode, (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]


@check("T1", "The package's own unit tests pass (necessary, NOT sufficient - see M1/M2)")
def t1():
    out, bad = [], False
    for pkg in ("transportlah", "namahatrix"):
        if not glob.glob(os.path.join(ROOT, pkg, "test*.py")):
            out.append("%s: NO TEST FILE" % pkg); bad = True; continue
        rc, tail = _unit_tests(pkg)
        out.append("%s: rc=%s %s" % (pkg, rc, tail[0])); bad |= rc != 0
    return ("FAIL" if bad else "PASS"), "\n".join(out)


def _mutate(pkg, fname, old, new):
    src = os.path.join(ROOT, pkg)
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, pkg)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.mp4"))
    p = os.path.join(dst, fname)
    s = read_text(p)
    if old not in s:
        shutil.rmtree(tmp, ignore_errors=True)
        return "NOMATCH"
    open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=dst, capture_output=True, text=True, timeout=180)
    shutil.rmtree(tmp, ignore_errors=True)
    return "KILLED" if r.returncode != 0 else "SURVIVED"


def _mutation_report(pkg, fname, muts):
    lines, survived, nomatch = [], 0, 0
    for label, old, new in muts:
        res = _mutate(pkg, fname, old, new)
        survived += res == "SURVIVED"; nomatch += res == "NOMATCH"
        lines.append("%-9s %s" % (res, label))
    status = "FAIL" if survived else ("WARN" if nomatch else "PASS")
    return status, "SURVIVED = your tests did not notice the code was broken.\n" + "\n".join(lines)


@check("M1", "MUTATION - TransportLah: break the verifier on purpose; its tests must notice every break")
def m1():
    if ARGS.skip_mutation:
        return "SKIP", "--skip-mutation"
    return _mutation_report("transportlah", "spatial_verification.py", [
        ("time-window filter disabled", 'if abs(c_epoch - vp["epoch"]) <= max_time_drift_sec', "if True"),
        ("distance threshold disabled", "if best_dist <= max_distance_threshold_m:", "if True:"),
        ("verdict always True", "is_verified = (match_ratio >= min_match_ratio)", "is_verified = True"),
        ("haversine 10x too small", "EARTH_RADIUS_KM * c * 1000.0", "EARTH_RADIUS_KM * c * 100.0"),
        ("min match ratio -> 0.0", "min_match_ratio: float = 0.75", "min_match_ratio: float = 0.0"),
    ])


@check("M2", "MUTATION - Namahatrix: break the judge/pipeline on purpose; its tests must notice every break")
def m2():
    if ARGS.skip_mutation:
        return "SKIP", "--skip-mutation"
    return _mutation_report("namahatrix", "agent_decoupling_runtime.py", [
        ("judge always approves", "is_approved = (len(violations) == 0)", "is_approved = True"),
        ("KMS invariant disabled", 'if not sec.get("kms_enclave_enabled"):', "if False:"),
        ("decoupling invariant disabled", 'if not topo.get("decoupling_verified"):', "if False:"),
        ("empty-modules invariant disabled", 'if not disc.get("discovered_modules"):', "if False:"),
        ("topology branch forced", "if peak_tps > 5000 or sync_blocking:", "if True:"),
    ])


# ================================================== E. CLAIM LINT: every claim needs evidence
def _code_has(rx):
    for p in walk_files((".py",)):
        if is_self(p) or os.path.basename(p).startswith(("test", "build_")):
            continue
        if re.search(rx, read_text(p), re.I):
            return True
    return False


def _has_evidence_file(pattern):
    return bool(glob.glob(EVID(pattern)))


RULES = [  # (name, claim regex, evidence description, evidence function)  None => never allowed
    ("PostGIS", r"postgis", "code that talks to a spatial DB (psycopg/asyncpg/ST_*)", lambda: _code_has(r"psycopg|asyncpg|sqlalchemy|ST_[A-Za-z]+\(")),
    ("jitter compensation", r"jitter.compensation", "smoothing/filtering code", lambda: _code_has(r"kalman|median|moving.average|smooth")),
    ("'eliminates 429s'", r"eliminat\w*[^.\n]{0,40}429", "an absolute claim; never provable", None),
    ("benchmarked", r"benchmark", "evidence/bench* (raw timing output)", lambda: _has_evidence_file("bench*")),
    ("percent-perfect / reduction figures", r"100% (deterministic|success|verified|confidence)|zero air|\b0% [^.\n]{0,30}block|\b90% [^.\n]{0,30}reduc", "evidence/bench* (measured numbers)", lambda: _has_evidence_file("bench*")),
    ("live / real-time LTA", r"(live|real.?time)[^.\n]{0,40}(LTA|DataMall|bus|vehicle)|(LTA|DataMall)[^.\n]{0,40}(live|real.?time)", "check C5 PASS (captured live response)", lambda: status_of("C5") == "PASS"),
    ("spoof rejection", r"reject\w*[^.\n]{0,30}spoof|anomaly detection|fraud", "check B9 PASS (not merely KNOWN)", lambda: status_of("B9") == "PASS"),
    ("decoupled / producer-consumer", r"decoupl\w*|producer.?/?consumer", "check D3 PASS (queue consumed)", lambda: status_of("D3") == "PASS"),
    ("immutable ledger", r"immutable", "frozen dataclass (frozen=True)", lambda: _code_has(r"frozen\s*=\s*True")),
    ("zero battery drain", r"zero.battery|battery.drain", "a client app (none in package)", None),
    ("genuine failure detection by judge", r"invariants? (evaluated|checked)|genuine\w* programmatic", "check D2 PASS (judge reachable via pipeline)", lambda: status_of("D2") == "PASS"),
]
SOFT = r"\b(authentic|genuine|robust|production.grade|enterprise.grade|battle.tested|verified with zero)\b"


def _surfaces():
    out = []
    for p in walk_files((".md", ".txt", ".py")):
        b = os.path.basename(p)
        if is_self(p) or b == "CLAIMS_AND_DELTA_AUDIT.md":
            continue
        if p.endswith(".py") and not b.startswith("build_"):
            continue  # code docstrings are covered by behavior checks; lint reads prose + video script
        if os.sep + "evidence" + os.sep in p and not b.endswith((".md", ".txt")):
            continue
        out.append(p)
    return out


FUTURE = re.compile(r"\b(integrate|implement|deploy|connect|days? \d|sprint \d|week \d|phase \d|roadmap|planned|will|todo|target|next steps?)\b", re.I)
IDENT = re.compile(r"[A-Za-z0-9]*_[A-Za-z0-9_]*|[A-Z][a-z]+[A-Z]\w*")   # snake_case / CamelCase identifiers are not claims


@check("L1", "CLAIM LINT: every strong claim in docs/receipts/video-script is backed by evidence (roadmap lines exempt)")
def l1():
    grouped, soft = {}, []
    for p in _surfaces():
        rel = os.path.relpath(p, ROOT)
        for n, line in enumerate(read_text(p).splitlines(), 1):
            for name, rx, need, ev in RULES:
                text = IDENT.sub(" ", line) if name.startswith("decoupled") else line
                if not re.search(rx, text, re.I):
                    continue
                if ev is not None and FUTURE.search(line):
                    continue                       # honest future work is not a claim about the present
                if (ev() if ev else False):
                    continue
                g = grouped.setdefault((rel, name, need), {"lines": [], "ex": line.strip()[:100]})
                g["lines"].append(n)
            if re.search(SOFT, line, re.I):
                soft.append("%s:%d" % (rel, n))
    out = []
    for (rel, name, need), g in sorted(grouped.items()):
        out.append("%s  [%s] x%d (lines %s)\n      needs: %s\n      e.g.:  %s" % (rel, name, len(g["lines"]), ",".join(map(str, g["lines"][:6])), need, g["ex"]))
    msg = "%d unsupported claim group(s)\n" % len(out) + "\n".join(out)
    if soft:
        msg += "\nPuffery words (delete): " + ", ".join(soft[:12])
    return ("FAIL" if out else "PASS"), msg


# ================================================== F. EVIDENCE HYGIENE
@check("R1", "Receipts are FRESH (newer than the code they vouch for) and contain exit codes")
def r1():
    code = [p for p in walk_files((".py",)) if not is_self(p) and not os.path.basename(p).startswith("build_")]
    newest = max(os.path.getmtime(p) for p in code) if code else 0
    recs = [p for p in walk_files((".txt", ".json", ".md")) if re.search(r"receipt|_output", os.path.basename(p), re.I)
            and os.sep + "evidence" + os.sep not in p]
    if not recs:
        return "WARN", "no receipt files found (fine, but then do not claim 'verified receipts')"
    bad = []
    for p in recs:
        t = read_text(p)
        if os.path.getmtime(p) < newest:
            bad.append("STALE      %s (older than newest code by %.0f min)" % (os.path.relpath(p, ROOT), (newest - os.path.getmtime(p)) / 60))
        if not re.search(r"exit[_ ]?code\s*[:=]\s*-?\d+", t, re.I):
            bad.append("NO EXITCODE %s" % os.path.relpath(p, ROOT))
    return ("FAIL" if bad else "PASS"), "\n".join(bad) or "all receipts fresh with exit codes"


@check("R2", "Internal audit/notes files are not inside the shippable package")
def r2():
    hits = [os.path.relpath(p, ROOT) for p in walk_files((".md", ".txt")) if re.search(r"AUDIT|DELTA|INTERNAL", os.path.basename(p), re.I)]
    junk = [os.path.relpath(p, ROOT) for p in walk_files((".pyc",))]
    junk += [os.path.relpath(p, ROOT) for p in walk_files((".py",)) if re.search(r'D:\\\\?anonym|D:\\\\?god_ai', read_text(p)) and not is_self(p)]
    msg = []
    if hits: msg.append("internal files: " + ", ".join(hits))
    if junk: msg.append("pyc / hardcoded private D:\\ paths in: " + ", ".join(junk[:8]))
    return ("WARN" if msg else "PASS"), "\n".join(msg) or "clean"


def _ffprobe_ok():
    return shutil.which("ffprobe") and shutil.which("ffmpeg")


@check("V1", "Videos: exist, and duration is close to the '2-minute' claim (PASS 105-135 s, WARN 90-165 s)")
def v1():
    vids = walk_files((".mp4", ".webm", ".mov"))
    if not vids:
        return "FAIL", "no video files. Emails claimed a recorded walkthrough."
    if not _ffprobe_ok():
        return "SKIP", "ffprobe/ffmpeg not installed; install ffmpeg to verify videos"
    out, worst = [], "PASS"
    for v in vids:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip() or 0)
        aud = len(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.split())
        out.append("%s: %.0fs, audio streams=%d%s" % (os.path.relpath(v, ROOT), dur, aud, "  (SILENT: do not call it a narrated walkthrough)" if aud == 0 else ""))
        if not 90 <= dur <= 165:
            worst = "FAIL"
        elif not 105 <= dur <= 135 and worst == "PASS":
            worst = "WARN"
    return worst, "\n".join(out)


@check("V2", "Videos: if you CALL it a live run/screen recording, it must show motion, not 5 static slides (declare with --video-label)")
def v2():
    vids = walk_files((".mp4", ".webm", ".mov"))
    if not vids or not _ffprobe_ok():
        return "SKIP", "no videos or no ffmpeg"
    out, static = [], False
    for v in vids:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", "fps=1,scale=32:18,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        n = len(raw) // 576
        frames = {bytes(b // 24 for b in raw[i * 576:(i + 1) * 576]) for i in range(n)}
        out.append("%s: %d distinct scenes in %d seconds" % (os.path.relpath(v, ROOT), len(frames), n)); static |= (n >= 60 and len(frames) <= 12)
    if not static:
        return "PASS", "\n".join(out)
    if ARGS.video_label == "slides":
        return "PASS", "static slides, and you declared them as slides. Describe them exactly so.\n" + "\n".join(out)
    return "FAIL", "static slideshow but declared 'live'. Re-run with --video-label slides ONLY if you will call it a slide walkthrough.\n" + "\n".join(out)


@check("V3", "Video script does not contain hand-typed 'terminal output' (log lines must come from a captured file)")
def v3():
    gens = [p for p in walk_files((".py",)) if os.path.basename(p).startswith("build_") and "video" in os.path.basename(p).lower()]
    if not gens:
        return "SKIP", "no video generator script found"
    bad = []
    for p in gens:
        t = read_text(p)
        typed = re.findall(r"(Verified: (?:True|False)|VERDICT: \w+|Confidence Score: ?[\d.]+|\[\d\d:\d\d:\d\d\])", t)
        reads_evidence = re.search(r"evidence|stdout|capture|\.read\(", t)
        if typed and not reads_evidence:
            bad.append("%s has %d typed log literals (e.g. %r) and reads no captured output" % (os.path.basename(p), len(typed), typed[0]))
    return ("FAIL" if bad else "PASS"), "\n".join(bad) or "log text comes from captured output"


# ================================================== modes
def capture_live():
    key = os.environ.get("LTA_DATAMALL_KEY")
    if not key:
        print("Set LTA_DATAMALL_KEY (free key from datamall.lta.gov.sg), then re-run."); return 2
    lp = load("transportlah", "lta_datamall_proxy")
    p = lp.LTADataMallProxy(api_key=key, cache_ttl_sec=0)
    raw = p.get_bus_arrival(ARGS.stop, ARGS.service)
    src = raw.get("_source")
    if src != "LIVE_NETWORK" or "Services" not in raw:
        print("FAILED: not a live response. source=%s error=%s" % (src, raw.get("message"))); return 1
    os.makedirs(os.path.dirname(EVID("x")), exist_ok=True)
    doc = {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "source": src, "stop": ARGS.stop, "service": ARGS.service,
           "raw": raw, "raw_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()}
    json.dump(doc, open(EVID("lta_live_capture.json"), "w", encoding="utf-8"), indent=2)
    print("OK: saved evidence/lta_live_capture.json (key not stored). Services returned: %d" % len(raw["Services"]))
    return 0


def write_receipt(exit_code):
    os.makedirs(os.path.dirname(EVID("x")), exist_ok=True)
    files = {os.path.relpath(p, ROOT): sha256(p) for p in walk_files((".py", ".md", ".mp4")) if os.sep + "evidence" + os.sep not in p}
    doc = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0], "platform": platform.platform(),
           "machine_tz_utc_offset_s": -time.timezone, "master_exit_code": exit_code,
           "results": RESULTS, "sha256": files}
    json.dump(doc, open(EVID("RUN_RECEIPT.json"), "w", encoding="utf-8"), indent=2)
    lines = ["MASTER CLAIMS TEST RECEIPT", "run_at_utc: " + doc["run_at_utc"], "python: %s  platform: %s" % (doc["python"], doc["platform"]),
             "exit_code: %d" % exit_code, ""]
    lines += ["%-5s %-4s %s" % (r["status"], r["id"], r["claim"]) for r in RESULTS]
    lines += ["", "sha256 of every file this receipt vouches for:"] + ["%s  %s" % (h, f) for f, h in sorted(files.items())]
    open(EVID("RUN_RECEIPT.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote evidence/RUN_RECEIPT.txt and .json")


def main():
    global ARGS, ROOT
    ap = argparse.ArgumentParser(description="Master claims test")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--video-label", choices=["live", "slides"], default="live")
    ap.add_argument("--max-age-hours", type=float, default=48)
    ap.add_argument("--capture-live", action="store_true")
    ap.add_argument("--stop", default="09048")
    ap.add_argument("--service", default="190")
    ap.add_argument("--write-receipt", action="store_true")
    ap.add_argument("--skip-mutation", action="store_true")
    ARGS = ap.parse_args()
    ROOT = os.path.abspath(ARGS.root)
    if ARGS.capture_live:
        return capture_live()
    print("ROOT:", ROOT)
    print("Python %s | %s | machine tz offset %ds\n" % (sys.version.split()[0], platform.system(), -time.timezone))
    run_all()
    counts = {}
    for r in RESULTS:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n" + "=" * 70)
    print("SUMMARY: " + "  ".join("%s=%d" % kv for kv in sorted(counts.items())))
    fails = [r["id"] for r in RESULTS if r["status"] == "FAIL"]
    print("VERDICT: " + ("NOT HONEST YET. Do not describe this package as verified. Failing: " + ", ".join(fails) if fails
          else "No unsupported claim found by these checks. WARN/KNOWN items must be disclosed, not hidden."))
    print("Passing this script proves the claims it tests - nothing more. Play the videos yourself before sending.")
    code = 1 if fails else 0
    if ARGS.write_receipt:
        write_receipt(code)
    return code


if __name__ == "__main__":
    sys.exit(main())
