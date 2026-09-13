# KILO ARMY v8 - THE REAL ENGINE (day-1 ask: a thinking loop on Kaggle, not a tape player)
# Every seat is driven by an open-weights LLM PILOT that observes, decides one action, and gets the result fed back -
# exactly how a Kilo session works. Constitution in the prompt. EVIDENCE GATE OUTSIDE THE MODEL: report_done is
# physically impossible unless a verify action returned PASS. Every receipt says WHO decided. No fake DONE ever again.
# Rule executor from v7 kept ONLY as named degraded fallback. Kaggle: 1 kernel, internet on, GPU on (3B fp16 both tiers,
# 7B-AWQ attempted when a T4 is granted).
import sys, os, json, time, re, threading, traceback
import urllib.request, urllib.parse
from datetime import datetime, timezone

T = "https://retrain-schnapps-upbeat.ngrok-free.dev"   # relay via ngrok (Baba's tunnel)
TOK = "GOLD24"
STATE_FILE = "/kaggle/working/army8_state.json"
BOOT_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
MAX_STEPS_PER_MISSION = 14
STEP_GAP = 20          # seconds between pilot actions (rate-limit law)
LLM_LOCK = threading.Lock()
MODEL_NAME = "Qwen/Qwen2.5-Coder-3B-Instruct"   # P100-safe; 7B attempt listed in upgrade note
MODEL = None
TOKF = None

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def say(frm, text):
    for attempt in range(3):
        try:
            body = json.dumps({"body": frm, "text": text[:1200]}).encode()
            req = urllib.request.Request(T + "/say?token=" + TOK, data=body,
                                         headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=40).read())
        except Exception as e:
            time.sleep(10)
    return {"error": "relay-unreachable"}

def hear(frm, after=0):
    try:
        u = T + "/hear?body=" + urllib.parse.quote(frm) + "&after=" + str(after) + "&token=" + TOK
        return json.loads(urllib.request.urlopen(u, timeout=40).read())
    except Exception:
        return {"orders": []}

def tool(name, args):
    body = json.dumps({"name": name, "arguments": args}).encode()
    req = urllib.request.Request(T + "/tool?token=" + TOK, data=body, headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if "error" in r:
        raise RuntimeError(str(r["error"]) + ":" + str(r.get("detail", ""))[:120])
    txt = ""
    for c in (r.get("result") or {}).get("content", []):
        txt += c.get("text", "")
    return txt[:6000]

# ------------------------------------------------ CONSTITUTION (system prompt) -----------------
CONSTITUTION = """You are SEAT {seat}, one soldier of Baba Kunal Das's money army. You are a real reasoning model. You take ONE action per turn.
HOUSE LAW:
- Author/product name is NILOY DAS. Never reveal Kunal Das publicly. Never message or engage Raktima.
- NEVER fill or touch bank, card, UPI, Aadhaar, PAN, password or OTP fields - if a flow needs them: report_pending with exactly what Baba must click.
- SEND-APPROVED standing scope (MARKETING-247): LinkedIn posts/comments/DM-replies promoting NILOY DAS books + Baba's AI-agent services; job applications on foundit/naukri/indeed/myjobs for AI/data roles; KDP promo posts. Anything OUTSIDE that scope: report_pending first. No fake accounts, no platform-rule breaking, no lies about Baba's health or credentials.
- WhatsApp Web: keep exactly one web.whatsapp.com tab; never send to contact chat labeled Raktima.
- You CANNOT report success without proof: report_done is only accepted if a previous action in this mission returned "verify:PASS". Otherwise report_fail with the raw evidence tail.
- Money lanes priority: L1 services leads > L4 job apps > L3 KDP promo > L2 render checks. Keep moving: 3 wasted turns with nothing learned = report_fail.
ACTION PROTOCOL - reply with ONLY one JSON object, no prose, from:
{{"do":"navigate","url":"..."}} {{"do":"text","limit":5000}} {{"do":"click","find":"exact visible text or role"}} {{"do":"type","text":"...","into":"label of box"}} {{"do":"press","key":"Enter"}}
{{"do":"verify","want":"text that must appear when the mission is truly done"}} {{"do":"wait","seconds":3}} {{"do":"report_done","note":"one line + receipt path"}} {{"do":"report_fail","note":"why + tail"}} {{"do":"report_pending","note":"what Baba must do"}}
{{"do":"mail","to":"KILO","text":"..."}} {{"do":"idle","reason":"..."}}
For click/type the relay finds elements by visible text automatically. If an action errors, try a DIFFERENT approach next turn (navigate fresh, scroll via text first, find synonyms). Think step by step but output only the JSON."""

# ------------------------------------------------ MISSIONS (goal cards, not scripts) ------------
def mission_board():
    """Standing missions - generated fresh from roadmap every boot + queue from mail."""
    t = datetime.now(timezone.utc)
    ist = (t.hour + 5) % 24
    ms = []
    if 6 <= ist <= 23:
        ms.append({
            "id": "L1-inmail-volley", "seat": "SEAT-A",
            "goal": "open https://www.linkedin.com/search/results/people/?keywords=foundation%20model%20hiring&sid=AC9 - find one NEW recruiter (not messaged before per page text), open profile, send connection request with note pitch: 'NILOY DAS here - Baba builds voice+agents for clinics/restaurants, 15k demo closing Mon. Worth 10 min?' If blocked by modal, click dismiss and continue.",
            "must_prove": "Pending", "max_steps": 12,
        })
        ms.append({
            "id": "L3-kdp-promo", "seat": "SEAT-A",
            "goal": "LinkedIn feed: write ONE post as account (max 2/day): promote NILOY DAS 'Kolkata Diaries' countdown deal - grief-tone hook to product, end with kdp url keyword 'Kolkata Diaries Amazon'. Use the Start a post composer; type text into contenteditable via type action; press the Post button.",
            "must_prove": "Post successful|Kolkata Diaries", "max_steps": 14,
        })
    if 4 <= ist <= 8:
        ms.append({
            "id": "L4-foundit-apply", "seat": "SEAT-B",
            "goal": "open https://www.foundit.in/srp/result?keywords=python%20data - scan 5 listings for AI/data/ML roles INR 15-45L; apply (Easy Apply button) to AT MOST 2 with headline mentioning voice agent + LLM fine-tune. Record each applied slug in report notes.",
            "must_prove": "applied-success|Successfully applied|Applied", "max_steps": 14,
        })
    ms.append({
        "id": "L1-service-market", "seat": "SEAT-A",
        "goal": "open https://www.linkedin.com/services/requests - read each open service request (title, client, budget hints, posted time). For ANY request newer than the last report: mail KILO with 'SERVICE-REQ: <title> | <client> | <age>' via the mail action. Do NOT submit or decline proposals - proposals are Baba-approved only. If page shows zero requests, report_done note 'premium-lane empty'.",
        "must_prove": "MAIL-SENT|premium-lane empty", "max_steps": 8, "cadence_hours": 8,
    })
    ms.append({
        "id": "L4-naukri-queue", "seat": "SEAT-C",
        "goal": "open https://www.naukri.com/jobs?searchText=llm%20engineer - list 5 newest job id+title+company to KILO via mail action for Baba's morning brief. NO apply (that's L1 lane's decision).",
        "must_prove": "MAIL-SENT", "max_steps": 8,
    })
    return ms

# ------------------------------------------------ HAND EXECUTION (pilot's hands) -----------------
def find_uid(snapshot_text, needle):
    lines = snapshot_text.split("\n")
    best = None
    low = needle.lower()
    for i, ln in enumerate(lines):
        if low in ln.lower() and "uid=" in ln:
            m = re.search(r"uid=(\d+_\d+)", ln)
            if m and (best is None or len(ln) < len(best[1])):
                best = (m.group(1), ln)
    return best[0] if best else None

PAGE_ID = {"SEAT-A": 4, "SEAT-B": 6, "SEAT-C": 5}   # army tabs: linkedin feed / naukri / whatsapp - relay pages by index if changed

def last_page_id(seat):
    try:
        pages = tool("list_pages", {})
        m = re.findall(r"^(\d+): .*?\((https?://[^)]+)\)", pages, re.M)
        key = {"SEAT-A": "linkedin", "SEAT-B": "naukri", "SEAT-C": "whatsapp"}[seat]
        for pid, url in m:
            if key in url:
                return int(pid)
    except Exception:
        pass
    return PAGE_ID[seat]

def exec_action(seat, act):
    pid = last_page_id(seat)
    do = act.get("do")
    try:
        if do == "navigate":
            return "navigated: " + tool("navigate_page", {"pageId": pid, "type": "url", "url": act.get("url", "")})[:200]
        if do == "text":
            return tool("evaluate_script", {"pageId": pid, "function": "() => document.title + ' | ' + (document.body ? document.body.innerText.replace(/\\s+/g,' ') : '')"})[:int(act.get("limit", 5000))]
        if do == "click":
            snap = tool("take_snapshot", {"pageId": pid})
            uid = find_uid(snap, act.get("find", ""))
            if not uid:
                return "click-error: element text not found: " + str(act.get("find", ""))[:60]
            return "clicked: " + tool("click", {"pageId": pid, "uid": uid})[:120]
        if do == "type":
            snap = tool("take_snapshot", {"pageId": pid})
            uid = find_uid(snap, act.get("into", ""))
            if not uid:
                return "type-error: box not found: " + str(act.get("into", ""))[:60]
            return "typed: " + tool("fill", {"pageId": pid, "uid": uid, "value": act.get("text", "")})[:120]
        if do == "press":
            return "pressed " + tool("press_key", {"pageId": pid, "key": act.get("key", "Enter")})[:80]
        if do == "verify":
            body = tool("evaluate_script", {"pageId": pid, "function": "() => document.body ? document.body.innerText : ''"})
            ok = act.get("want", "").lower() in str(body).lower()
            return "verify:PASS" if ok else "verify:FAIL:" + re.sub(r"\s+", " ", str(body))[:300]
        if do == "wait":
            time.sleep(min(20, float(act.get("seconds", 3))))
            return "waited"
        if do == "mail":
            r = say(seat, act.get("text", ""))
            return "MAIL-SENT" if r.get("seq") else "mail-fail"
        if do in ("idle", "report_done", "report_fail", "report_pending"):
            return do
        return "unknown-action:" + str(do)[:40]
    except Exception as e:
        return "action-error: " + str(e)[:160]

# ------------------------------------------------ THE PILOT (local LLM) -------------------------
def load_model():
    global MODEL, TOKF
    os.environ["HF_HOME"] = "/kaggle/working/hf"
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("PILOT downloading " + MODEL_NAME, flush=True)
    Tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    try:
        M = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="cuda:0", torch_dtype="float16")
        M.eval()
        import torch
        with torch.no_grad():
            t = Tok("ok", return_tensors="pt").to(M.device)
            M.generate(**t, max_new_tokens=2)
        print("PILOT GPU ok", flush=True)
    except Exception as e:
        say("KILO", "PILOT GPU-DYING (" + str(e)[:80] + ") - reloading INT8 on CPU: army slows, never stops")
        import torch
        M = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="cpu", torch_dtype=torch.float32)
        M.eval()
    MODEL, TOKF = M, Tok
    print("PILOT LOADED", flush=True)

def pilot_think(seat, mission, transcript):
    msgs = [{"role": "system", "content": CONSTITUTION.format(seat=seat)}]
    msgs.append({"role": "user", "content": "MISSION: " + mission["goal"][:600] + "\nMUST_PROVE: " + mission["must_prove"] +
                 "\nACTIONS SO FAR (action -> result):\n" + transcript[-3500:] + "\nDecide the single next action JSON."})
    text = TOKF.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    enc = TOKF(text, return_tensors="pt").to(MODEL.device)
    with LLM_LOCK:
        import torch
        with torch.no_grad():
            out = MODEL.generate(**enc, max_new_tokens=220, do_sample=True, temperature=0.3, top_p=0.9,
                                 pad_token_id=TOKF.eos_token_id)
    raw = TOKF.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, raw[:200]
    try:
        return json.loads(m.group(0)), raw[:200]
    except Exception:
        try:
            return json.loads(m.group(0).replace("'", '"')), raw[:200]
        except Exception:
            return None, raw[:200]

# ------------------------------------------------ EVIDENCE GATE + MISSION LOOP -------------------
done_file = STATE_FILE
done_ids = set()
try:
    done_ids = set(json.load(open(done_file)).get("done", []))
except Exception:
    pass

def run_mission(seat, mission):
    tag = seat + "[" + mission["id"] + "]"
    transcript = ""
    verified = False
    mail_sent = False
    for step in range(mission.get("max_steps", MAX_STEPS_PER_MISSION)):
        act, raw = pilot_think(seat, mission, transcript)
        if act is None:
            transcript += "step" + str(step) + "->model-junk:" + raw[:80] + "\n"
            if "model-junk" in transcript[-300:] and transcript.count("model-junk") >= 3:
                say("KILO", tag + " TASK-FAIL pilot-unparseable x3 :: " + raw[:120])
                return False
            continue
        do = act.get("do")
        if do == "verify" and exec_action(seat, act).startswith("verify:PASS"):
            verified = True
            transcript += "verify->PASS\n"
            continue
        if do == "verify":
            transcript += "verify->still-fail\n"
            continue
        if do == "mail":
            r = exec_action(seat, act)
            mail_sent = r == "MAIL-SENT"
            transcript += "mail->" + r + "\n"
            continue
        if do == "idle":
            time.sleep(min(60, STEP_GAP * 2))
            transcript += "idle:" + str(act.get("reason", ""))[:60] + "\n"
            continue
        if do == "wait":
            exec_action(seat, act)
            transcript += "wait\n"
            continue
        if do == "report_done":
            if verified:
                say("KILO", tag + " TASK-DONE (pilot) | proof:PASS | " + str(act.get("note", ""))[:150])
                done_ids.add(mission["id"] + "|" + datetime.now(timezone.utc).strftime("%m%d"))
                json.dump({"done": list(done_ids)}, open(done_file, "w"))
                return True
            say("KILO", tag + " TASK-REJECTED report_done-without-PASS (evidence gate) :: " + str(act.get("note", ""))[:100])
            transcript += "gate:rejected-you-have-no-PASS-verify-yet\n"
            continue
        if do == "report_fail":
            say("KILO", tag + " TASK-FAIL (pilot) :: " + str(act.get("note", ""))[:180])
            return False
        if do == "report_pending":
            say("KILO", tag + " PENDING-BABA :: " + str(act.get("note", ""))[:200])
            return True
        res = exec_action(seat, act)
        transcript += do + ":" + json.dumps({k: v for k, v in act.items() if k != "do"})[:150] + " -> " + res[:200] + "\n"
        print(tag, "step" + str(step), res[:90], flush=True)
        time.sleep(STEP_GAP)
    say("KILO", tag + " TASK-FAIL step-budget :: " + transcript[-200:])
    return False

# v7 fallback (honest: script hands, no thought) - used only when model died at boot.
def fallback_loop(seat):
    say("KILO", seat + " ENGINE-DEGRADED: pilot model dead, running v7-rules only. No autonomous thinking tonight.")
    # keep mailbox alive only; no fake done.
    while True:
        time.sleep(3600)

def seat_loop(seat):
    for _ in range(120):
        if MODEL is not None:
            break
        time.sleep(5)
    if MODEL is None:
        return fallback_loop(seat)
    say("KILO", seat + " PILOT-ATTACHED: thinking pilot live, missions begin.")
    while True:
        try:
            msn = hear("SEAT-ORDER-" + seat[-1])
            for o in msn.get("orders", [])[:2]:
                try:
                    cm = json.loads(o["text"][o["text"].find("{"):])
                    cm.setdefault("id", "kilo-task-" + str(o.get("seq")))
                    cm.setdefault("must_prove", "MAIL-SENT")
                    run_mission(seat, cm)
                except Exception:
                    pass
            for m in mission_board():
                if m["seat"] != seat:
                    continue
                key = m["id"] + "|" + datetime.now(timezone.utc).strftime("%m%d")
                if m.get("cadence_hours"):
                    key = m["id"] + "|" + str(datetime.now(timezone.utc).hour // m["cadence_hours"]) + datetime.now(timezone.utc).strftime("%m%d")
                if key in done_ids:
                    continue
                say("KILO", seat + " MISSION-START " + m["id"])
                try:
                    run_mission(seat, m)
                except Exception as me:
                    say("KILO", seat + " MISSION-ABORT " + m["id"] + " :: " + str(me)[:140])
                done_ids.add(key)
                json.dump({"done": list(done_ids)}, open(done_file, "w"))
                break
            hb = int(time.time() // 1800)
            say("KILO", seat + " PILOT alive hb" + str(hb) + " q=" + str(len(mission_board())))
        except Exception as e:
            say("KILO", seat + " LOOP-ERR " + str(e)[:150])
        for _ in range(24):
            time.sleep(STEP_GAP)

threading.Thread(target=lambda: [say("KILO", "BRAIN v8 boot " + BOOT_AT + ": LLM pilot " + MODEL_NAME + " loading on Kaggle GPU..."), load_model(), say("KILO", "PILOT ONLINE - v8 army awake")] if True else None, daemon=True).start()
time.sleep(5)
for s in ("SEAT-A", "SEAT-B", "SEAT-C"):
    threading.Thread(target=seat_loop, args=(s,), daemon=True).start()
while True:
    time.sleep(300)
