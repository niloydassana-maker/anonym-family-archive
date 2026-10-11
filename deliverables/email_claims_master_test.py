#!/usr/bin/env python3
"""
EMAIL CLAIMS MASTER TEST  --  "is every sentence in the Aveek mail earned?"

Stdlib only (ffmpeg/ffprobe/tesseract are used if installed, skipped if not).

    python email_claims_master_test.py --root .                  # run everything
    python email_claims_master_test.py --root . --email mail.txt # test an edited mail
    python email_claims_master_test.py --root . --prior-email earlier.txt --attest A2,F1
    python email_claims_master_test.py --root . --write-receipt  # evidence/EMAIL_CLAIMS_RECEIPT.*
    python email_claims_master_test.py --root . --strict         # WARN / UNVERIFIED also fail

Layout expected under --root:  transportlah/ (code, tests, .md, .mp4)  [+ transportlah_output.txt,
build_walkthrough_videos.py, evidence/RUN_RECEIPT.json  -- used when present]

HOW IT WORKS
  1. The mail text is split into sentences. Every sentence must contain a registered claim
     (or be an explicit no-claim sentence). Edit the mail and add a claim -> this test fails
     until you map it. That is what makes it a *master* test of "all claims in the mail".
  2. Each claim has checks that CAN fail: behaviour (run the code with inputs that must be
     rejected), differential fuzz against an independent reference, artifact checks (video
     duration / motion / OCR'd text), and cross-document consistency.
  3. META: the verifier is deliberately broken 5 ways; this suite's own battery must notice
     every break. A survivor means the suite proves nothing.
  4. Claims about the past or about people (earlier email, batchmates) cannot be tested by
     code. They are reported UNVERIFIED unless you supply evidence (--prior-email) or attest
     (--attest). They never silently pass.

STATUSES   PASS | FAIL | WARN | UNVERIFIED | ATTESTED | INFO | SKIP
EXIT CODE  1 if any FAIL (or any WARN/UNVERIFIED with --strict), else 0.
"""
import argparse, ast, glob, hashlib, importlib.util, json, math, os, platform, random, re
import shutil, subprocess, sys, tempfile, time, traceback
import urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# --------------------------------------------------------------------------- THE MAIL
EMAIL = r"""Hi Aveek,

Circling back on TransportLah with a direct, personal note.

Looking back at my earlier commercial email, I realized my automated proposal framework made things sound overly rigid and transactional — especially the upfront advance terms and the automated sign-off. We're college batchmates, and that wasn't the right way to frame an engineering collaboration.

I've already set up the core Singapore LTA DataMall proxy and the PostGIS spatial verification pipeline on our test bench. I put together a clean 2-minute walkthrough showing the arrival timestamp correlation and ride verification logic running live.

Take a look whenever you have a moment — zero obligation.

If you like the architecture, we can simply run a 10-day Sprint 1 pilot to get the TestFlight build into your hands, structured on verified milestones rather than heavy upfront commitments.
"""

# Sentences that carry no testable claim (greeting / framing). Matched by prefix.
NO_CLAIM_PREFIX = ["Hi Aveek", "Circling back on TransportLah", "If you like the architecture"]
# NB: the last one is only exempt as a *conditional*; its payload (F2/F3/F4) is still required
# to be registered below, so the sentence must ALSO contain a claim quote (enforced in E0).

# --------------------------------------------------------------------------- CLAIM REGISTRY
# kind: ARTIFACT (exists now) | BEHAVIOR | FUTURE (promise) | NARRATIVE (past/people)
CLAIMS = {
    "A1": dict(kind="NARRATIVE", quote="the upfront advance terms and the automated sign-off",
               fix="Nothing to change if the earlier mail really had these. Supply it with --prior-email."),
    "A2": dict(kind="NARRATIVE", quote="We're college batchmates",
               fix="Personal fact. Only you can attest it (--attest A2)."),
    "P1": dict(kind="ARTIFACT", quote="I've already set up the core Singapore LTA DataMall proxy",
               fix="True as 'set up'. Do not imply it has talked to the real LTA yet (see V4)."),
    "P2": dict(kind="ARTIFACT", quote="the PostGIS spatial verification pipeline",
               fix="\"a Python (haversine) spatial verification engine -- PostGIS is the planned production store\""),
    "P3": dict(kind="ARTIFACT", quote="on our test bench",
               fix="\"on a local test bench\" (nothing is hosted; 'our' implies shared infrastructure)"),
    "V1": dict(kind="ARTIFACT", quote="clean 2-minute walkthrough",
               fix="\"a ~2.5-minute walkthrough\" (or trim to <= 2:10); regenerate slide 5, which wrongly says a single ping passes"),
    "V2": dict(kind="BEHAVIOR", quote="arrival timestamp correlation",
               fix="\"commuter-vs-vehicle timestamp correlation on recorded test data\""),
    "V3": dict(kind="BEHAVIOR", quote="ride verification logic",
               fix="Earned for well-formed input. Malformed pings raise instead of rejecting; disclose replay / 90 m limits."),
    "V4": dict(kind="ARTIFACT", quote="running live",
               fix="\"running on recorded Singapore test data (live LTA feed is the first Sprint 1 item)\""),
    "F1": dict(kind="NARRATIVE", quote="zero obligation",
               fix="A promise, not a fact. Make sure nothing you attach asks for payment."),
    "F2": dict(kind="FUTURE", quote="10-day Sprint 1 pilot",
               fix="Fine if the Sprint 1 scope you send matches what the mail promises (see F3)."),
    "F3": dict(kind="FUTURE", quote="get the TestFlight build into your hands",
               fix="Add TestFlight/iOS client to the written Sprint 1 plan, or soften to 'a first test build'."),
    "F4": dict(kind="FUTURE", quote="structured on verified milestones rather than heavy upfront commitments",
               fix="Attach a MILESTONES.md: each milestone = one acceptance check from this suite + payment share."),
    "SHIP": dict(kind="ARTIFACT", quote=None,
                 fix="Send transportlah/ + its video only -- not deliverables.zip."),
}

RANK = {"FAIL": 5, "WARN": 4, "UNVERIFIED": 3, "ATTESTED": 2, "PASS": 1, "INFO": 0, "SKIP": 0}

ARGS = None
ROOT = None
RESULTS = []        # dict(id, claims, status, desc, evidence)
CHECKS = []         # (id, claims, desc, fn)


# --------------------------------------------------------------------------- harness
def check(cid, claims, desc):
    def deco(fn):
        CHECKS.append((cid, claims, desc, fn))
        return fn
    return deco


def emit(cid, claims, status, desc, evidence=""):
    RESULTS.append(dict(id=cid, claims=claims, status=status, desc=desc, evidence=str(evidence)))
    print("[%-10s] %-5s (%s) %s" % (status, cid, ",".join(claims), desc))
    for line in str(evidence).splitlines():
        print("             " + line)


def read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tl(*p):
    return os.path.join(ROOT, "transportlah", *p)


def tl_files(exts):
    out = []
    for d, dirs, files in os.walk(tl()):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        out += [os.path.join(d, f) for f in files if f.lower().endswith(exts)]
    return sorted(out)


def prod_py():
    return [p for p in tl_files((".py",)) if not os.path.basename(p).startswith("test")]


def load(mod, root=None):
    path = os.path.join(root or ROOT, "transportlah", mod + ".py")
    spec = importlib.util.spec_from_file_location("tl_" + mod, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def norm(s):
    return re.sub(r"\s+", " ", s.replace("\u2019", "'").replace("\u2018", "'")).strip()


def sentences(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            out += [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return out


# --------------------------------------------------------------------------- fixtures
BASE = datetime(2026, 10, 10, 23, 55, 0, tzinfo=timezone.utc)
BUS_PTS = [(1.3048, 103.8318, 0), (1.3015, 103.8385, 180), (1.2990, 103.8450, 360)]
M_PER_DEG = 111194.93


def iso(sec, z=True):
    d = BASE + timedelta(seconds=sec)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ" if z else "%Y-%m-%dT%H:%M:%S")


def bus():
    return [{"lat": a, "lng": b, "timestamp": iso(t)} for a, b, t in BUS_PTS]


def ride(dlat_m=0.0, dt=0, z=True):
    return [{"lat": a + dlat_m / M_PER_DEG, "lng": b, "timestamp": iso(t + dt, z)} for a, b, t in BUS_PTS]


def verify(mod, commuter, veh=None, **kw):
    kw.setdefault("max_distance_threshold_m", 100.0)
    kw.setdefault("max_time_drift_sec", 30.0)
    return mod.SpatialVerificationEngine.verify_transit_segment(commuter, veh or bus(), **kw)


# --------------------------------------------------------------------------- core battery
def battery(root=None):
    """Behavioural scenarios for the verifier. Returns [(name, ok, detail)]."""
    tv = load("spatial_verification", root)
    out = []

    def add(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    r = verify(tv, ride(dlat_m=30, dt=4))
    add("genuine ride (30 m jitter, +4 s) verified 3/3", r["verified"] and r["matched_pings"] == 3, r.get("reasons"))
    add("same places, +12 h rejected", not verify(tv, ride(dt=12 * 3600))["verified"])
    add("London rejected", not verify(tv, [{"lat": 51.5074, "lng": -0.1278, "timestamp": iso(0)}] * 3)["verified"])
    stay = [{"lat": 1.3049, "lng": 103.8319, "timestamp": iso(t)} for _, _, t in BUS_PTS]
    add("never-moved passenger rejected", not verify(tv, stay)["verified"])
    rev = [{"lat": BUS_PTS[2 - i][0], "lng": BUS_PTS[2 - i][1], "timestamp": iso(BUS_PTS[i][2])} for i in range(3)]
    add("reversed route rejected", not verify(tv, rev)["verified"])
    a, b = verify(tv, ride(dlat_m=50))["verified"], verify(tv, ride(dlat_m=150))["verified"]
    add("distance limit exact: 50 m ok / 150 m rejected", a and not b, "50m=%s 150m=%s" % (a, b))
    a, b = verify(tv, ride(dt=25))["verified"], verify(tv, ride(dt=35))["verified"]
    add("time limit exact: +25 s ok / +35 s rejected", a and not b, "+25s=%s +35s=%s" % (a, b))
    add("single-ping 'ride' rejected", not verify(tv, [ride()[0]])["verified"])
    add("empty input rejected", not verify(tv, [])["verified"])
    garbage = []
    for name, c in (("missing-ts", [{"lat": 1.3, "lng": 103.8}] * 3),
                    ("nan-lat", [{"lat": float("nan"), "lng": 103.8, "timestamp": iso(0)}] * 3),
                    ("bad-ts", [{"lat": 1.3, "lng": 103.8, "timestamp": "not-a-time"}] * 3)):
        try:
            garbage.append((name, verify(tv, c)["verified"] is False))
        except Exception as e:
            garbage.append((name, False))
    add("garbage (missing/NaN/bad timestamp) fails safe", all(g for _, g in garbage), str(garbage))
    if os.name == "posix":
        tlpath = os.path.join(root or ROOT, "transportlah")
        child = ("import sys; sys.path.insert(0, %r)\nfrom spatial_verification import SpatialVerificationEngine as S\n"
                 "v=[{'lat':1.3048,'lng':103.8318,'timestamp':'2026-10-10T23:55:00Z'}]\n"
                 "c=[{'lat':1.3049,'lng':103.8319,'timestamp':'2026-10-10T23:55:04'}]*2\n"
                 "print(S.verify_transit_segment(c,v,max_distance_threshold_m=100.0,max_time_drift_sec=30.0)['verified'])\n") % tlpath
        verdicts = {}
        for tz in ("UTC", "Asia/Kolkata", "Asia/Singapore", "America/New_York"):
            verdicts[tz] = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True,
                                          env=dict(os.environ, TZ=tz)).stdout.strip()
        add("naive timestamp gives same verdict in 4 machine timezones", len(set(verdicts.values())) == 1, str(verdicts))
    return out


# --------------------------------------------------------------------------- E0: coverage of the mail
@check("E0.1", ["SHIP"], "Mail is fully mapped: every sentence holds a registered claim or is a declared no-claim")
def e0_1():
    sents = sentences(EMAIL_TEXT())
    unmapped, mapped = [], 0
    for s in sents:
        ns = norm(s)
        hit = [cid for cid, c in CLAIMS.items() if c["quote"] and norm(c["quote"]) in ns]
        exempt = any(ns.startswith(norm(p)) for p in NO_CLAIM_PREFIX)
        if hit:
            mapped += 1
        elif not exempt:
            unmapped.append(s)
    if unmapped:
        return "FAIL", "UNMAPPED sentence(s) -- add a claim for each:\n" + "\n".join("  - " + u for u in unmapped)
    return "PASS", "%d sentences, all mapped or declared no-claim" % len(sents)


@check("E0.2", ["SHIP"], "Every registered claim quote still appears in the mail (no orphan claims)")
def e0_2():
    text = norm(EMAIL_TEXT())
    orphans = [cid for cid, c in CLAIMS.items() if c["quote"] and norm(c["quote"]) not in text]
    return ("FAIL" if orphans else "PASS"), ("orphans: %s" % orphans) if orphans else "all %d quotes anchor" % sum(1 for c in CLAIMS.values() if c["quote"])


def EMAIL_TEXT():
    if ARGS and ARGS.email:
        return read_text(ARGS.email)
    return EMAIL


# --------------------------------------------------------------------------- P1: LTA proxy
class _Resp:
    def __init__(self, payload):
        self._p = payload
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(self._p).encode()


def _fake_urlopen(fn, raises=None):
    real, seen = urllib.request.urlopen, []
    def fake(req, timeout=None):
        seen.append(req)
        if raises:
            raise raises
        return _Resp({"BusStopCode": "00000", "Services": []})
    urllib.request.urlopen = fake
    try:
        return fn(seen)
    finally:
        urllib.request.urlopen = real


def _new_proxy(lp, **kw):
    saved = {k: os.environ.pop(k, None) for k in ("LTA_DATAMALL_KEY", "LTA_KEY_PATH")}
    try:
        return lp.LTADataMallProxy(**kw)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


@check("P1.1", ["P1", "P3"], "Proxy imports, and with no key runs in labelled OFFLINE_FIXTURE mode; unknown stop = error, not invented data")
def p1_1():
    lp = load("lta_datamall_proxy")
    p = _new_proxy(lp)
    known, unknown = p.get_bus_arrival("09048", "190"), p.get_bus_arrival("99999", "1")
    ok = (p.mode == "OFFLINE_FIXTURE" and known.get("_source") == "OFFLINE_FIXTURE" and known.get("Services")
          and unknown.get("error") is True and not unknown.get("Services"))
    return ("PASS" if ok else "FAIL"), "mode=%s known._source=%s unknown.error=%s" % (p.mode, known.get("_source"), unknown.get("error"))


@check("P1.2", ["P1"], "TTL cache really suppresses repeat requests (2 calls in TTL -> 1 request; after TTL -> 2)")
def p1_2():
    lp = load("lta_datamall_proxy")
    def go(seen):
        p = lp.LTADataMallProxy(api_key="TESTKEY", cache_ttl_sec=0.3)
        p.get_bus_arrival("09048", "190"); p.get_bus_arrival("09048", "190")
        inside = len(seen); time.sleep(0.45); p.get_bus_arrival("09048", "190")
        return inside, len(seen)
    inside, after = _fake_urlopen(go)
    return ("PASS" if (inside, after) == (1, 2) else "FAIL"), "inside TTL=%d, after expiry=%d (want 1, 2)" % (inside, after)


@check("P1.3", ["P1"], "Outages and HTTP 429 are surfaced as errors with status code -- never papered over with fixture data")
def p1_3():
    lp = load("lta_datamall_proxy")
    res = {}
    for name, exc in (("outage", urllib.error.URLError("simulated")),
                      ("429", urllib.error.HTTPError("https://x", 429, "Too Many Requests", {}, None))):
        r = _fake_urlopen(lambda seen: lp.LTADataMallProxy(api_key="TESTKEY").get_bus_arrival("09048", "190"), raises=exc)
        res[name] = (r.get("error") is True and not r.get("Services") and "ERROR" in str(r.get("_source"))
                     and (name != "429" or r.get("status_code") == 429), r.get("_source"), r.get("status_code"))
    return ("PASS" if all(v[0] for v in res.values()) else "FAIL"), str(res)


@check("P1.4", ["P1"], "Live request shape: https, datamall host, /BusArrival with BusStopCode+ServiceNo, AccountKey header; key never echoed back")
def p1_4():
    lp = load("lta_datamall_proxy")
    def go(seen):
        r = lp.LTADataMallProxy(api_key="TESTKEY-123").get_bus_arrival("09048", "190")
        return seen[0], r
    req, r = _fake_urlopen(go)
    hdr = {k.lower(): v for k, v in req.header_items()}
    url = req.full_url
    ok = (url.startswith("https://datamall") and "/BusArrival?" in url and "BusStopCode=09048" in url
          and "ServiceNo=190" in url and hdr.get("accountkey") == "TESTKEY-123" and "TESTKEY-123" not in json.dumps(r))
    return ("PASS" if ok else "FAIL"), "url=%s  accountkey_header=%s  key_in_result=%s" % (url, "accountkey" in hdr, "TESTKEY-123" in json.dumps(r))


# --------------------------------------------------------------------------- P2: "PostGIS" + verification logic
PG_RX = re.compile(r"\bpsycopg2?\b|\basyncpg\b|\bsqlalchemy\b|\bgeoalchemy2?\b|\bST_[A-Z][A-Za-z]+\s*\(|\bCREATE\s+EXTENSION\s+postgis", re.I)


@check("P2.1", ["P2"], "'PostGIS pipeline': code EXECUTES SQL against PostGIS (DB-driver import + execute call). SQL strings, .sql and compose files alone do not count")
def p2_1():
    DRV = ("psycopg", "psycopg2", "asyncpg", "sqlalchemy", "geoalchemy2")
    drv, exe, sqlfn = [], [], {}
    trees = {}
    for p in prod_py():
        try:
            trees[p] = ast.parse(read_text(p))
        except SyntaxError:
            continue
    for p, tree in trees.items():
        rel = os.path.relpath(p, ROOT)
        for n in ast.walk(tree):
            names = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else \
                    [(n.module or "").split(".")[0]] if isinstance(n, ast.ImportFrom) else []
            if any(x in DRV for x in names):
                drv.append("%s:%d" % (rel, n.lineno))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("execute", "executemany"):
                exe.append("%s:%d" % (rel, n.lineno))
            if isinstance(n, ast.FunctionDef):
                body_txt = ast.get_source_segment(read_text(p), n) or ""
                if re.search(r"\bST_[A-Z]\w+\s*\(", body_txt):
                    sqlfn[n.name] = rel
    callers = {k: sum(len(re.findall(r"\b%s\s*\(" % k, read_text(q))) - (1 if q == os.path.join(ROOT, v) else 0)
                     for q in trees) for k, v in sqlfn.items()}
    side = []
    if glob.glob(tl("*.sql")): side.append("schema .sql present")
    if glob.glob(tl("docker-compose*")): side.append("docker-compose present")
    if drv and exe:
        return "UNVERIFIED", "driver import %s and execute() %s exist, but nothing here proves it runs against a real PostGIS (needs a parity run)" % (drv[:2], exe[:2])
    return "FAIL", ("no code executes SQL: driver imports=%s, execute() calls=%s.\n"
                    "SQL-generating functions: %s (callers outside definition: %s).\n"
                    "Artifacts without a runtime path: %s. The engine still matches in pure-Python haversine."
                    % (drv or "none", exe or "none", sorted(sqlfn) or "none", callers or "n/a", side or "none"))


@check("P2.2", ["P2"], "The package's own docs agree with the word 'PostGIS' (not contradict it)")
def p2_2():
    rx = re.compile(r"without external GIS|pure Python[^.\n]{0,60}(math|GIS)|no (external )?(GIS )?database", re.I)
    found = []
    for p in tl_files((".md", ".txt")):
        for n, line in enumerate(read_text(p).splitlines(), 1):
            if rx.search(line):
                found.append("%s:%d  %s" % (os.path.relpath(p, ROOT), n, line.strip()[:110]))
    text, how = corpus()
    for line in text.splitlines():
        if rx.search(line):
            found.append("video (%s): %s" % (how.split()[0], line.strip()[:110]))
    if found:
        return "FAIL", "package says the OPPOSITE of the mail:\n" + "\n".join(found[:4])
    return "PASS", "no contradicting statement in docs"


@check("P2.3", ["P2", "V3"], "Verification logic behaves: accepts genuine ride; rejects wrong time/place/stationary/reversed/single-ping/garbage; limits exact")
def p2_3():
    res = battery()
    bad = [(n, d) for n, ok, d in res if not ok]
    lines = ["%s %s" % ("ok  " if ok else "BAD ", n) for n, ok, d in res]
    return ("FAIL" if bad else "PASS"), "\n".join(lines)


@check("P2.4", ["P2", "V3"], "Differential fuzz: 2,000 random scenarios agree with an independent reference verifier (incl. exact boundaries)")
def p2_4():
    tv = load("spatial_verification")
    rnd = random.Random(11)
    mism, tested, skipped = [], 0, 0
    def ref(c, v, D=100.0, T=30.0, R=0.75):
        m = 0
        for clat, clng, ct in c:
            ok = False
            for vlat, vlng, vt in v:
                if abs(ct - vt) <= T:
                    dy = (clat - vlat) * M_PER_DEG
                    dx = (clng - vlng) * M_PER_DEG * math.cos(math.radians((clat + vlat) / 2))
                    ok |= math.hypot(dx, dy) <= D
            m += ok
        return (len(c) >= 2 and m / len(c) >= R), m
    def near_boundary(c, v):
        for clat, clng, ct in c:
            for vlat, vlng, vt in v:
                if abs(ct - vt) <= 30.0 + 1:
                    dy = (clat - vlat) * M_PER_DEG
                    dx = (clng - vlng) * M_PER_DEG * math.cos(math.radians((clat + vlat) / 2))
                    if abs(math.hypot(dx, dy) - 100.0) < 1.0:
                        return True
        return False
    for _ in range(2000):
        pings = []
        for _k in range(rnd.randint(1, 5)):
            a, b, t = rnd.choice(BUS_PTS)
            if rnd.random() < 0.12:
                lat, lng = 1.30 + rnd.uniform(-.02, .02), 103.84 + rnd.uniform(-.02, .02)
            else:
                d, th = rnd.uniform(0, 200), rnd.uniform(0, 6.2832)
                lat, lng = a + d * math.sin(th) / M_PER_DEG, b + d * math.cos(th) / (M_PER_DEG * math.cos(math.radians(a)))
            dt = rnd.choice([rnd.randint(-50, 50)] * 9 + [rnd.randint(-7200, 7200)])
            pings.append((lat, lng, t + dt))
        vref = [(a, b, t) for a, b, t in BUS_PTS]
        if near_boundary(pings, vref):
            skipped += 1
            continue
        tested += 1
        want, wm = ref(pings, vref)
        got = verify(tv, [{"lat": a, "lng": b, "timestamp": iso(t)} for a, b, t in pings])
        if got["verified"] != want or got["matched_pings"] != wm:
            mism.append((pings, want, got["verified"], wm, got["matched_pings"]))
    if mism:
        return "FAIL", "%d/%d disagree. first: want=%s got=%s matched want=%s got=%s" % (len(mism), tested, mism[0][1], mism[0][2], mism[0][3], mism[0][4])
    return "PASS", "%d scenarios agree with reference (%d skipped within 1 m of the 100 m edge)" % (tested, skipped)


@check("P2.5", ["P2", "V3"], "Robustness probe: structurally malformed pings (missing lat/lng, None, string coords) do not crash")
def p2_5():
    tv = load("spatial_verification")
    crashes = []
    for name, c in (("missing-lat", [{"lng": 103.8, "timestamp": iso(0)}] * 3),
                    ("none-coords", [{"lat": None, "lng": None, "timestamp": iso(0)}] * 3),
                    ("string-coords", [{"lat": "abc", "lng": "def", "timestamp": iso(0)}] * 3)):
        try:
            if verify(tv, c)["verified"]:
                crashes.append("%s: APPROVED" % name)
        except Exception as e:
            crashes.append("%s: %s" % (name, type(e).__name__))
    return ("WARN" if crashes else "PASS"), ("raises instead of returning verified=False: " + "; ".join(crashes)) if crashes else "all fail safe"


@check("P2.6", ["V3"], "INFO -- limits the mail does NOT mention: replay of the bus's own public feed, and 90 m pedestrian")
def p2_6():
    tv = load("spatial_verification")
    replay = verify(tv, bus())["verified"]
    walker = verify(tv, ride(dlat_m=90))["verified"]
    disclosed = any("KNOWN LIMIT" in read_text(p) for p in tl_files((".md",)))
    return "INFO", "replay accepted=%s  90m-pedestrian accepted=%s  disclosed in docs=%s (do not claim spoof/fraud resistance)" % (replay, walker, disclosed)


MUTATIONS = [
    ("time-window filter removed", 'if abs(c_epoch - vp["epoch"]) <= max_time_drift_sec', "if True"),
    ("distance threshold removed", "if best_dist <= max_distance_threshold_m:", "if True:"),
    ("verdict always True", "is_verified = (match_ratio >= min_match_ratio)", "is_verified = True"),
    ("single-ping guard removed", "            is_verified = False", "            pass"),
    ("haversine 10x too small", "EARTH_RADIUS_KM * c * 1000.0", "EARTH_RADIUS_KM * c * 100.0"),
]


@check("M0", ["P2", "V3"], "META: break the verifier 5 ways; this suite's own battery must catch every break")
def m0():
    if ARGS.skip_mutation:
        return "SKIP", "--skip-mutation"
    lines, survived, nomatch = [], 0, 0
    for label, old, new in MUTATIONS:
        tmp = tempfile.mkdtemp()
        try:
            dst = os.path.join(tmp, "transportlah")
            shutil.copytree(tl(), dst, ignore=shutil.ignore_patterns("__pycache__", "*.mp4"))
            p = os.path.join(dst, "spatial_verification.py")
            s = read_text(p)
            if old not in s:
                nomatch += 1; lines.append("NOMATCH   " + label); continue
            open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "--root", tmp, "--battery-only"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                survived += 1
            lines.append(("SURVIVED  " if r.returncode == 0 else "KILLED    ") + label)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    status = "FAIL" if survived else ("WARN" if nomatch else "PASS")
    return status, "SURVIVED = the suite did not notice the code was broken.\n" + "\n".join(lines)


# --------------------------------------------------------------------------- P3: test bench / receipts
def _clean_room():
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "transportlah")
    shutil.copytree(tl(), dst, ignore=shutil.ignore_patterns("__pycache__", "*.mp4"))
    return tmp, dst


def _env_nokey():
    return {k: v for k, v in os.environ.items() if k not in ("LTA_DATAMALL_KEY", "LTA_KEY_PATH")}


_DEMO = {}


def demo_run():
    if "r" not in _DEMO:
        tmp, dst = _clean_room()
        try:
            r = subprocess.run([sys.executable, "demo_runner.py"], cwd=dst, capture_output=True, text=True, timeout=90, env=_env_nokey())
            _DEMO["r"] = (r.returncode, r.stdout.replace("\r\n", "\n"), r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return _DEMO["r"]


@check("P3.1", ["P3"], "Clean-room reproduction: demo runs from a fresh copy (no key, no private paths), exit 0, shows a pass AND a rejection")
def p3_1():
    rc, out, err = demo_run()
    ok = rc == 0 and "Verified: True" in out and "Verified: False" in out
    return ("PASS" if ok else "FAIL"), "exit=%s  has True=%s has False=%s  stderr=%r" % (rc, "Verified: True" in out, "Verified: False" in out, err[:120])


@check("P3.2", ["P3", "V4"], "Shipped receipt (transportlah_output.txt) is reproducible: its stdout equals a fresh run's stdout")
def p3_2():
    rp = os.path.join(ROOT, "transportlah_output.txt")
    if not os.path.exists(rp):
        return "SKIP", "no transportlah_output.txt"
    t = read_text(rp).replace("\r\n", "\n")
    m = re.search(r"--- STDOUT ---\n(.*?)\n--- STDERR ---", t, re.S)
    exit_ok = re.search(r"EXIT_CODE:\s*0", t)
    if not m:
        return "FAIL", "receipt has no STDOUT section"
    _, fresh, _ = demo_run()
    same = m.group(1).strip() == fresh.strip()
    return ("PASS" if same and exit_ok else "FAIL"), "stdout identical=%s  receipt exit code 0=%s" % (same, bool(exit_ok))


@check("P3.3", ["P3", "V3"], "Package unit tests pass; count matches the '8 automated unit tests' stated in the video")
def p3_3():
    tmp, dst = _clean_room()
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=dst, capture_output=True, text=True, timeout=120)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = re.search(r"Ran (\d+) tests?", r.stderr)
    n = int(n.group(1)) if n else -1
    _DEMO["tests"] = n
    return ("PASS" if r.returncode == 0 and n > 0 else "FAIL"), "rc=%s tests=%s" % (r.returncode, n)


@check("P3.4", ["P3"], "Receipt vouches for the bytes shipped: sha256 in evidence/RUN_RECEIPT.json matches current transportlah/* files")
def p3_4():
    rp = os.path.join(ROOT, "evidence", "RUN_RECEIPT.json")
    if not os.path.exists(rp):
        return "SKIP", "no evidence/RUN_RECEIPT.json"
    doc = json.load(open(rp, encoding="utf-8"))
    mism, ok, missing = [], 0, []
    for rel, h in doc.get("sha256", {}).items():
        relp = rel.replace("\\", "/")
        if not relp.startswith("transportlah/"):
            continue
        p = os.path.join(ROOT, *relp.split("/"))
        if not os.path.exists(p):
            missing.append(relp)
        elif sha256(p) == h:
            ok += 1
        else:
            mism.append(relp)
    st = "FAIL" if (mism or missing) else "PASS"
    return st, "match=%d changed-since-receipt=%s missing=%s" % (ok, mism, missing)


@check("P3.5", ["SHIP"], "No private machine paths, leftover .pyc, or hard-coded passwords inside what you would send (transportlah/)")
def p3_5():
    bad = []
    for p in tl_files((".py", ".md", ".txt")):
        if re.search(r"[A-Z]:\\+(anonym|god_ai)", read_text(p)):
            bad.append(os.path.relpath(p, ROOT))
    bad += [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(tl(), "**", "*.pyc"), recursive=True)]
    for p in glob.glob(tl("docker-compose*")):
        if re.search(r"PASSWORD:\s*\S+", read_text(p)):
            bad.append(os.path.relpath(p, ROOT) + " (hard-coded DB password; fine locally, never reuse it)")
    return ("WARN" if bad else "PASS"), ("found in: " + ", ".join(bad)) if bad else "clean"


@check("P3.6", ["P3"], "INFO -- 'our test bench': is anything hosted/remote that Aveek could reach?")
def p3_6():
    rx = re.compile(r"https?://(?!datamall2\.mytransport\.sg)[^\s\"']+|0\.0\.0\.0|serve_forever|HTTPServer|uvicorn|flask", re.I)
    hits = [os.path.relpath(p, ROOT) for p in prod_py() if rx.search(read_text(p))]
    return "INFO", "server/hosted endpoints in package: %s => it is a LOCAL bench; Aveek can only watch the video or run it himself" % (hits or "none")


# --------------------------------------------------------------------------- V1/V2/V4: the video
def _vid():
    v = glob.glob(tl("*.mp4"))
    return v[0] if v else None


def _have_ff():
    return bool(shutil.which("ffprobe") and shutil.which("ffmpeg"))


def _probe(v, stream):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", "stream=codec_type", "-of", "csv=p=0", v],
                          capture_output=True, text=True).stdout.split()


@check("V1.1", ["V1"], "A walkthrough video exists in the package")
def v1_1():
    v = _vid()
    return ("PASS", os.path.relpath(v, ROOT)) if v else ("FAIL", "no .mp4 in transportlah/")


@check("V1.2", ["V1"], "Duration matches '2-minute' (PASS within 10%, WARN within 25%, FAIL beyond)")
def v1_2():
    v = _vid()
    if not v or not _have_ff():
        return "SKIP", "no video or ffprobe"
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip() or 0)
    dev = abs(dur - 120) / 120
    return ("PASS" if dev <= .10 else "WARN" if dev <= .25 else "FAIL"), "%.0f s = %d:%02d  (%.0f%% off 2:00)" % (dur, dur // 60, dur % 60, dev * 100)


@check("V1.3", ["V1"], "INFO -- audio track present? (silent video should not be called 'narrated')")
def v1_3():
    v = _vid()
    if not v or not _have_ff():
        return "SKIP", "no video or ffprobe"
    n = len(_probe(v, "a"))
    return "INFO", "audio streams=%d%s" % (n, "  (silent)" if n == 0 else "")


_CORPUS = {}


def corpus():
    """Text the viewer actually sees. OCR of one frame per slide if tesseract exists; else the build script."""
    if "c" in _CORPUS:
        return _CORPUS["c"]
    v = _vid()
    if v and _have_ff() and shutil.which("tesseract"):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip() or 0)
        tmp, texts = tempfile.mkdtemp(), []
        try:
            for i in range(6):
                png = os.path.join(tmp, "f%d.png" % i)
                subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.1f" % (dur / 6 * (i + .5)), "-i", v, "-frames:v", "1", png], capture_output=True)
                if os.path.exists(png):
                    texts.append(subprocess.run(["tesseract", png, "stdout"], capture_output=True, text=True, timeout=90).stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        _CORPUS["c"] = ("\n".join(texts), "OCR of rendered frames")
    else:
        bs = os.path.join(ROOT, "build_walkthrough_videos.py")
        if os.path.exists(bs):
            parts = read_text(bs).split("slides = [")
            _CORPUS["c"] = (parts[1] if len(parts) > 2 else read_text(bs), "build-script text (NOT OCR: install tesseract+ffmpeg for stronger evidence)")
        else:
            _CORPUS["c"] = ("", "none")
    return _CORPUS["c"]


@check("V1.4", ["V1"], "What the video SAYS matches what the code DOES (single-ping behaviour, unit-test count)")
def v1_4():
    text, how = corpus()
    if not text:
        return "SKIP", "no video text available"
    flat = re.sub(r"\s+", " ", text)
    problems = []
    if re.search(r"single[- ]?ping.{0,140}?(satisf|passes|accepted)", flat, re.I):
        rejects = not verify(load("spatial_verification"), [ride()[0]])["verified"]
        if rejects:
            problems.append("video says a single ping PASSES; the code (and WALKTHROUGH_OVERVIEW.md) REJECT it")
    m = re.search(r"(\d+)\s+automated unit tests", flat, re.I)
    if m:
        if "tests" not in _DEMO:
            p3_3()
        if int(m.group(1)) != _DEMO.get("tests"):
            problems.append("video says %s unit tests; actual run = %s" % (m.group(1), _DEMO.get("tests")))
    if re.search(r"zero unearned claims", flat, re.I):
        problems.append("footer 'Zero unearned claims' is an absolute claim this suite shows is false (see FAILs)")
    return ("FAIL" if problems else "PASS"), "(%s)\n" % how + ("\n".join(problems) or "consistent")


@check("V2.1", ["V2"], "'Arrival timestamp correlation' uses the proxy's data: EVERY vehicle-trajectory point is derived from proxy output, none hand-typed")
def v2_1():
    tree = ast.parse(read_text(tl("demo_runner.py")))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "vehicle_trajectory" for t in node.targets):
            if not isinstance(node.value, ast.List):
                return "PASS", "trajectory built by expression, not a literal list"
            lit = [e for e in node.value.elts if isinstance(e, ast.Dict) and all(isinstance(v, ast.Constant) for v in e.values)]
            n = len(node.value.elts)
            if lit:
                return "FAIL", "%d of %d vehicle points are hand-typed literals; only the rest touch proxy output" % (len(lit), n)
            return "PASS", "all %d points derived from proxy output" % n
    return "WARN", "vehicle_trajectory assignment not found in demo_runner.py"


@check("V2.2", ["V2"], "All timestamps in the demo use ONE consistent UTC offset, matching the proxy's (no Z / +08:00 mixing = the original 8-hour bug)")
def v2_2():
    lp = load("lta_datamall_proxy")
    fx = lp.LTADataMallProxy.RECORDED_FIXTURES["09048"]["190"]["NextBus"]["EstimatedArrival"]
    want = re.search(r"(Z|[+-]\d\d:\d\d)$", fx).group(1)
    offs = re.findall(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(Z|[+-]\d\d:\d\d)?", read_text(tl("demo_runner.py")))
    kinds = sorted({o or "NAIVE" for o in offs})
    ok = kinds == [want]
    return ("PASS" if ok else "FAIL"), "offsets used in demo_runner.py: %s; proxy ETA uses %s" % (kinds, want)


@check("V2.3", ["V2"], "Polling accumulates a REAL time series: successive polls give distinct positions, and the demo actually uses it")
def v2_3():
    lp = load("lta_datamall_proxy")
    meths = [m for m in dir(lp.LTADataMallProxy) if re.match(r"(poll|accumulate|record)_", m)]
    if not meths:
        return "WARN", "no poll/accumulate method: nothing turns repeated LTA polls into a trajectory"
    m = meths[0]
    real, n = urllib.request.urlopen, [0]
    def fake(req, timeout=None):
        n[0] += 1
        return _Resp({"BusStopCode": "09048", "Services": [{"ServiceNo": "190", "NextBus": {
            "Latitude": 1.30 + n[0] * 0.001, "Longitude": 103.83, "EstimatedArrival": "2026-10-10T23:%02d:00+08:00" % (n[0] % 60)}}]})
    urllib.request.urlopen = fake
    try:
        t0 = time.time()
        traj = getattr(lp.LTADataMallProxy(api_key="TESTKEY", cache_ttl_sec=30), m)("09048", "190")
        took = time.time() - t0
    finally:
        urllib.request.urlopen = real
    distinct = len({round(x["lat"], 6) for x in traj}) if traj else 0
    used = m in read_text(tl("demo_runner.py"))
    problems = []
    if distinct < 2:
        problems.append("%s() returned %d sample(s) but only %d distinct position(s) in %.2f s: repeated polls hit the 30 s cache or run back-to-back, so the 'trajectory' is copies of one reading" % (m, len(traj), distinct, took))
    if not used:
        problems.append("demo_runner.py never calls %s()" % m)
    return ("FAIL" if problems else "PASS"), "\n".join(problems) or "%s(): %d distinct positions" % (m, distinct)


@check("V4.1", ["V4"], "Video shows MOTION if called 'running live' (a slideshow of <=12 distinct scenes in >=60 s is not a live run)")
def v4_1():
    v = _vid()
    if not v or not _have_ff():
        return "SKIP", "no video or ffmpeg"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", "fps=1,scale=32:18,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // 576
    scenes = {bytes(b // 24 for b in raw[i * 576:(i + 1) * 576]) for i in range(n)}
    static = n >= 60 and len(scenes) <= 12
    if static and ARGS.video_label == "slides":
        return "PASS", "%d distinct scenes in %d s -- declared as slides (so the mail must say 'slides', not 'live')" % (len(scenes), n)
    return ("FAIL" if static else "PASS"), "%d distinct scenes in %d s%s" % (len(scenes), n, "  => static slideshow, not a live run" if static else "")


@check("V4.2", ["V4"], "The data-source label is TRUTHFUL: with no API key the demo must not print LIVE_NETWORK, and shipped receipts must show real LIVE data")
def v4_2():
    rc, fresh, _ = demo_run()
    if "LIVE_NETWORK" in fresh:
        lp = load("lta_datamall_proxy")
        return "FAIL", ("with NO key the proxy is %s, yet demo_runner.py prints LIVE_NETWORK: the label is hard-coded, so any 'live' receipt or video made from it proves nothing."
                        % _new_proxy(lp).mode)
    text, how = corpus()
    rp = os.path.join(ROOT, "transportlah_output.txt")
    blob = text + (read_text(rp) if os.path.exists(rp) else "")
    if "OFFLINE_FIXTURE" in blob or not re.search(r"LIVE_NETWORK", blob):
        return "FAIL", "shipped receipt/video show OFFLINE_FIXTURE or no live label"
    return "PASS", "no-key run is labelled OFFLINE; shipped receipt/video carry a LIVE label"


@check("V4.3", ["V4"], "LIVE proof file is plausible: not the offline fixture, ETAs lie ahead of capture time, hash intact, recent")
def v4_3():
    p = os.path.join(ROOT, "evidence", "lta_live_capture.json")
    if not os.path.exists(p):
        return "FAIL", "no evidence/lta_live_capture.json. Get a free AccountKey at datamall.lta.gov.sg, set LTA_DATAMALL_KEY, run:  python email_claims_master_test.py --capture-live"
    d = json.load(open(p, encoding="utf-8"))
    cap = datetime.fromisoformat(d["captured_at_utc"])
    age = (datetime.now(timezone.utc) - cap).total_seconds() / 3600
    h_ok = hashlib.sha256(json.dumps(d.get("raw"), sort_keys=True).encode()).hexdigest() == d.get("raw_sha256")
    shape = d.get("source") == "LIVE_NETWORK" and isinstance(d.get("raw"), dict) and "Services" in d["raw"]
    problems = []
    fx = load("lta_datamall_proxy").LTADataMallProxy.RECORDED_FIXTURES.get(str(d.get("stop")), {}).get(str(d.get("service")), {})
    for svc in d.get("raw", {}).get("Services", []):
        for key in ("NextBus", "NextBus2", "NextBus3"):
            nb, f = svc.get(key) or {}, fx.get(key) or {}
            same = [k for k in ("EstimatedArrival", "Latitude", "Longitude") if f and nb.get(k) == f.get(k)]
            if len(same) == 3:
                problems.append("%s equals the hand-typed OFFLINE fixture in ETA, latitude and longitude" % key)
            try:
                lead = (datetime.fromisoformat(nb["EstimatedArrival"]) - cap).total_seconds() / 3600
                if lead < -0.1:
                    problems.append("%s ETA is %.1f h BEFORE capture time (a live arrival estimate points forward)" % (key, -lead))
            except Exception:
                pass
    if not (shape and h_ok) or age > ARGS.max_age_hours:
        problems.append("shape_ok=%s hash_ok=%s age=%.1fh (max %sh)" % (shape, h_ok, age, ARGS.max_age_hours))
    note = "\n(note: raw_sha256 is computed by the capturer, so it only shows the file was not edited AFTER capture, not that LTA produced it. Re-capture yourself with --capture-live.)"
    return ("FAIL" if problems else "PASS"), ("\n".join(problems) or "plausible live capture") + note


@check("V4.4", ["V4"], "The package does not list 'live LTA key' as Sprint 1 TO-DO while the mail says it is already running live")
def v4_4():
    text, how = corpus()
    flat = re.sub(r"\s+", " ", text)
    m = re.search(r"Sprint 1[^.]{0,80}live LTA key", flat, re.I)
    return ("FAIL" if m else "PASS"), ("video roadmap itself says: %r" % m.group(0)) if m else "no contradiction"


@check("X1", ["P2", "V4"], "Package does not contradict the mail: its own roadmap must not list PostGIS or live-LTA as PLANNED/future while the mail says they are already done")
def x1():
    hits = []
    for p in tl_files((".md",)):
        t = read_text(p)
        for blk in re.split(r"(?m)^#{2,4} ", t):
            if not re.search(r"ROADMAP|FUTURE|\bPlanned\b|\bTarget\b", blk):
                continue
            head = blk.splitlines()[0][:90] if blk.strip() else ""
            if re.search(r"postgis", blk, re.I):
                hits.append(("P2", os.path.relpath(p, ROOT), head))
            if re.search(r"LIVE_NETWORK|live (AccountKey|API)|live LTA|Production LTA", blk, re.I):
                hits.append(("V4", os.path.relpath(p, ROOT), head))
    if hits:
        return "FAIL", "\n".join("[%s] %s lists as PLANNED: %s" % h for h in hits)
    return "PASS", "no roadmap item contradicts an 'already done' claim"


# --------------------------------------------------------------------------- F: promises
@check("F1.1", ["F1", "F4"], "Nothing shipped with the mail asks for money (no advance/deposit/retainer/invoice wording in transportlah/ or its video)")
def f1_1():
    rx = re.compile(r"\b(advance payment|upfront payment|up-front|retainer|deposit|invoice|pay(ment)? (of|terms))\b", re.I)
    hits = []
    for p in tl_files((".md", ".txt", ".py")):
        for n, l in enumerate(read_text(p).splitlines(), 1):
            if rx.search(l):
                hits.append("%s:%d" % (os.path.relpath(p, ROOT), n))
    return ("FAIL" if hits else "PASS"), ("payment wording at: " + ", ".join(hits)) if hits else "no payment language shipped"


@check("F2.1", ["F2"], "'10-day Sprint 1' matches the written roadmap (Sprint 1 = Days 1-10)")
def f2_1():
    text, how = corpus()
    flat = re.sub(r"\s+", " ", text)
    m = re.search(r"Sprint 1 \(Days? ?1.{0,3}10", flat, re.I)
    return ("PASS" if m else "WARN"), "(%s) %s" % (how, "roadmap says Sprint 1 = Days 1-10" if m else "no 'Sprint 1 (Days 1-10)' line found")


@check("F3.1", ["F3"], "The written Sprint 1 plan includes the TestFlight/iOS deliverable the mail promises")
def f3_1():
    text, how = corpus()
    flat = re.sub(r"\s+", " ", text)
    m = re.search(r"Sprint 1[^.]{0,120}", flat, re.I)
    plan = m.group(0) if m else "(no Sprint 1 line found)"
    mentions = re.search(r"testflight|\bios\b|iphone|app store|mobile app", plan, re.I)
    return ("PASS" if mentions else "WARN"), "written Sprint 1 scope: %r -- %s" % (plan[:130], "mentions iOS/TestFlight" if mentions else "no TestFlight/iOS item. Mail and plan disagree")


@check("F3.2", ["F3"], "INFO -- is there ANY client-app code today? (the 'Commuter App' box in the architecture)")
def f3_2():
    rx = re.compile(r"\b(swift|swiftui|xcodeproj|testflight|react.native|flutter|kotlin|\.ipa|info\.plist)\b", re.I)
    hits = [os.path.relpath(p, ROOT) for p in tl_files((".py", ".md", ".txt", ".swift", ".json", ".plist")) if rx.search(read_text(p))]
    swift = glob.glob(os.path.join(ROOT, "**", "*.swift"), recursive=True) + glob.glob(os.path.join(ROOT, "**", "*.xcodeproj"), recursive=True)
    return "INFO", "client-app files: %s. => TestFlight in 10 days is 100%% future work (that is allowed, but say it)." % (hits + swift or "NONE")


@check("F3.3", ["F3"], "Human preconditions for a TestFlight build (cannot be tested by code)")
def f3_3():
    return "UNVERIFIED", ("confirm yourself before promising a date:\n  [ ] Apple Developer Program membership active (whose account?)\n"
                          "  [ ] bundle ID + App Store Connect record\n  [ ] who writes the iOS GPS-capture client (none exists)\n  [ ] who is on the TestFlight tester list")


@check("F4.1", ["F4"], "'Verified milestones' are defined: a MILESTONES.md where each milestone names an acceptance check")
def f4_1():
    cands = glob.glob(os.path.join(ROOT, "**", "MILESTONE*.md"), recursive=True)
    if not cands:
        return "WARN", ("no MILESTONES.md. A 'verified milestone' needs a pass/fail test both of you can run. Suggested gates from this suite:\n"
                        "  M1 live LTA capture            -> check V4.3 PASS\n  M2 PostGIS-backed verification -> check P2.1 PASS + P2.4 PASS\n"
                        "  M3 TestFlight build installs   -> manual: Aveek installs it\n  (attach payment share to each gate)")
    t = read_text(cands[0])
    ok = len(re.findall(r"(?im)^\s*[-*]?\s*ACCEPT\w*\s*:", t)) >= 1
    return ("PASS" if ok else "WARN"), "%s: %s" % (os.path.relpath(cands[0], ROOT), "has ACCEPT: lines" if ok else "no 'ACCEPT:' acceptance lines")


# --------------------------------------------------------------------------- A: narrative / people
@check("A1.1", ["A1"], "Earlier mail really had 'upfront advance' terms (needs the earlier mail: --prior-email FILE)")
def a1_1():
    if not ARGS.prior_email:
        return ("ATTESTED", "attested by you") if "A1" in ATTEST else ("UNVERIFIED", "earlier email not provided. Re-run with --prior-email earlier.txt, or --attest A1")
    t = read_text(ARGS.prior_email)
    adv = re.search(r"\b(advance|upfront|up-front|deposit|50 ?%|retainer)\b", t, re.I)
    return ("PASS" if adv else "FAIL"), "advance-terms wording %s in prior email" % ("found" if adv else "NOT found")


@check("A2.1", ["A2"], "Personal assertion (college batchmates)")
def a2_1():
    return ("ATTESTED", "attested by you") if "A2" in ATTEST else ("UNVERIFIED", "cannot be code-tested. --attest A2 if true")


@check("F1.2", ["F1"], "Promise: 'zero obligation' -- you must honour it (attestation)")
def f1_2():
    return ("ATTESTED", "attested by you") if "F1" in ATTEST else ("UNVERIFIED", "a promise, not a fact. --attest F1 once you've checked F1.1 and your next mail")


# --------------------------------------------------------------------------- SHIP hygiene
@check("H1", ["SHIP"], "What you send for Aveek (transportlah/ + video) names no OTHER client")
def h1():
    rx = re.compile(r"Arjun|Chowdhury|Namahatrix", re.I)
    hits = [os.path.relpath(p, ROOT) for p in tl_files((".md", ".txt", ".py")) if rx.search(read_text(p))]
    text, how = corpus()
    if rx.search(text):
        hits.append("video text")
    return ("FAIL" if hits else "PASS"), ("other-client names in: " + ", ".join(hits)) if hits else "clean"


@check("H2", ["SHIP"], "deliverables.zip as a whole is safe to send to Aveek (no other client's package inside)")
def h2():
    other = [d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and d.lower() not in ("transportlah", "evidence", "video_frames", "__pycache__")]
    leaks = []
    for d in other:
        for p in glob.glob(os.path.join(ROOT, d, "**", "*"), recursive=True):
            if os.path.isfile(p) and p.lower().endswith((".md", ".py", ".txt")) and re.search(r"Prepared for:\*{0,2}\s*\S+", read_text(p)):
                leaks.append(os.path.relpath(p, ROOT))
    bs = os.path.join(ROOT, "build_walkthrough_videos.py")
    if os.path.exists(bs) and re.search(r"Client: (?!Aveek)\w+", read_text(bs)):
        leaks.append("build_walkthrough_videos.py (names another client)")
    return ("WARN" if leaks else "PASS"), ("zip also contains: " + ", ".join(leaks[:5]) + "  => send transportlah/ only") if leaks else "only TransportLah material"


# --------------------------------------------------------------------------- modes
ATTEST = set()


def capture_live():
    key = os.environ.get("LTA_DATAMALL_KEY")
    if not key:
        print("Set LTA_DATAMALL_KEY (free key from datamall.lta.gov.sg), then re-run with --capture-live."); return 2
    lp = load("lta_datamall_proxy")
    raw = lp.LTADataMallProxy(api_key=key, cache_ttl_sec=0).get_bus_arrival(ARGS.stop, ARGS.service)
    if raw.get("_source") != "LIVE_NETWORK" or "Services" not in raw:
        print("FAILED: not a live response: source=%s msg=%s" % (raw.get("_source"), raw.get("message"))); return 1
    os.makedirs(os.path.join(ROOT, "evidence"), exist_ok=True)
    doc = dict(captured_at_utc=datetime.now(timezone.utc).isoformat(), source="LIVE_NETWORK", stop=ARGS.stop, service=ARGS.service,
               raw=raw, raw_sha256=hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest())
    json.dump(doc, open(os.path.join(ROOT, "evidence", "lta_live_capture.json"), "w", encoding="utf-8"), indent=2)
    print("OK: evidence/lta_live_capture.json saved (key NOT stored). Services: %d" % len(raw["Services"])); return 0


def roll_up():
    per = {}
    for r in RESULTS:
        for c in r["claims"]:
            per.setdefault(c, []).append(r["status"])
    return {c: max(v, key=lambda s: RANK[s]) for c, v in per.items()}


def write_receipt(code, rolled):
    ev = os.path.join(ROOT, "evidence"); os.makedirs(ev, exist_ok=True)
    files = {os.path.relpath(p, ROOT): sha256(p) for p in tl_files((".py", ".md", ".mp4"))}
    doc = dict(run_at_utc=datetime.now(timezone.utc).isoformat(), python=sys.version.split()[0], platform=platform.platform(),
               exit_code=code, email_sha256=hashlib.sha256(norm(EMAIL_TEXT()).encode()).hexdigest(), claim_verdicts=rolled,
               results=RESULTS, sha256=files)
    json.dump(doc, open(os.path.join(ev, "EMAIL_CLAIMS_RECEIPT.json"), "w", encoding="utf-8"), indent=2)
    lines = ["EMAIL CLAIMS MASTER TEST RECEIPT", "run_at_utc: " + doc["run_at_utc"], "exit_code: %d" % code, "",
             "CLAIM VERDICTS: " + ", ".join("%s=%s" % kv for kv in sorted(rolled.items())), ""]
    lines += ["%-10s %-5s %s" % (r["status"], r["id"], r["desc"]) for r in RESULTS]
    open(os.path.join(ev, "EMAIL_CLAIMS_RECEIPT.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote evidence/EMAIL_CLAIMS_RECEIPT.txt and .json")


def main():
    global ARGS, ROOT, ATTEST
    ap = argparse.ArgumentParser(description="Master test of every claim in the Aveek mail")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--email", help="file with the mail text (default: embedded copy)")
    ap.add_argument("--prior-email", help="file with the earlier commercial email (for claim A1)")
    ap.add_argument("--attest", default="", help="comma list of claim ids you personally attest, e.g. A2,F1")
    ap.add_argument("--video-label", choices=["live", "slides"], default="live",
                    help="how the mail DESCRIBES the video. 'slides' is the honest label for the current video")
    ap.add_argument("--max-age-hours", type=float, default=48)
    ap.add_argument("--capture-live", action="store_true")
    ap.add_argument("--stop", default="09048"); ap.add_argument("--service", default="190")
    ap.add_argument("--skip-mutation", action="store_true")
    ap.add_argument("--battery-only", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--write-receipt", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ARGS = ap.parse_args()
    ROOT = os.path.abspath(ARGS.root)
    ATTEST = {x.strip().upper() for x in ARGS.attest.split(",") if x.strip()}
    if ARGS.battery_only:
        res = battery()
        bad = [n for n, ok, _ in res if not ok]
        print("battery: %d/%d ok" % (len(res) - len(bad), len(res)), bad)
        return 1 if bad else 0
    if ARGS.capture_live:
        return capture_live()

    print("ROOT:", ROOT)
    print("Python %s | %s | tz offset %ds | video-label=%s\n" % (sys.version.split()[0], platform.system(), -time.timezone, ARGS.video_label))
    for cid, claims, desc, fn in CHECKS:
        try:
            status, evidence = fn()
        except Exception:
            status, evidence = "FAIL", "EXCEPTION (check could not run):\n" + traceback.format_exc(limit=3)
        emit(cid, claims, status, desc, evidence)

    rolled = roll_up()
    print("\n" + "=" * 78 + "\nCLAIM-BY-CLAIM VERDICT (worst check wins)\n" + "=" * 78)
    order = list(CLAIMS.keys())
    for cid in order:
        v = rolled.get(cid, "SKIP")
        q = CLAIMS[cid]["quote"] or "(attachments / delivery)"
        print("%-10s %-5s %s" % (v, cid, q))
        if RANK[v] >= RANK["WARN"]:
            print("             say instead: " + CLAIMS[cid]["fix"])
    counts = {}
    for r in RESULTS:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\nCHECKS: " + "  ".join("%s=%d" % kv for kv in sorted(counts.items())))
    fails = [c for c in order if rolled.get(c) == "FAIL"]
    soft = [c for c in order if rolled.get(c) in ("WARN", "UNVERIFIED")]
    bad = fails + (soft if ARGS.strict else [])
    print("VERDICT: " + ("DO NOT SEND AS WRITTEN. Unearned claim(s): %s" % ", ".join(fails) if fails else
                         "No claim is contradicted by evidence. Open items: %s" % (", ".join(soft) or "none")))
    print("Passing proves only what the checks test. Watch the video yourself before sending.")
    code = 1 if bad else 0
    if ARGS.write_receipt:
        write_receipt(code, rolled)
    return code


if __name__ == "__main__":
    sys.exit(main())
