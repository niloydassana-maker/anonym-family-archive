# -*- coding: utf-8 -*-
"""AGENT SCHOOL - COHORT 1 : 72-slide deck generator (4 sessions x 18 slides)."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

OUT = r"D:\anonym\career\agent-school\AGENT-SCHOOL-SLIDES.pptx"

DARK_BLUE = RGBColor(0x15, 0x2C, 0x51)
DEEP_BLUE = RGBColor(0x0E, 0x1F, 0x3B)
GREEN     = RGBColor(0x1E, 0x9E, 0x6A)
ORANGE    = RGBColor(0xF3, 0x9C, 0x12)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG  = RGBColor(0xF5, 0xF7, 0xFA)
GREY      = RGBColor(0x5A, 0x64, 0x73)
CODE_BG   = RGBColor(0x10, 0x18, 0x28)
CODE_TX   = RGBColor(0x9C, 0xE3, 0xB0)

SW, SH = Inches(13.333), Inches(7.5)
FOOTER = "AGENT SCHOOL — COHORT 1"

prs = Presentation()
prs.slide_width = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]

def _box(slide, l, t, w, h):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb

def _rect(slide, l, t, w, h, color):
    from pptx.enum.shapes import MSO_SHAPE
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    sp.line.fill.background()
    sp.shadow.inherit = False
    return sp

def _set(p, text, size, color, bold=False, align=PP_ALIGN.LEFT, font="Calibri", space_after=6):
    p.text = text
    p.alignment = align
    p.space_after = Pt(space_after)
    for r in p.runs:
        r.font.size = Pt(size); r.font.color.rgb = color
        r.font.bold = bold; r.font.name = font

def new_slide():
    return prs.slides.add_slide(BLANK)

def footer(slide, num, dark=False):
    c = RGBColor(0xB9, 0xC4, 0xD6) if dark else GREY
    tb = _box(slide, Inches(0.4), Inches(7.02), Inches(6), Inches(0.4))
    _set(tb.text_frame.paragraphs[0], FOOTER, 11, c, font="Calibri")
    tb2 = _box(slide, Inches(12.2), Inches(7.02), Inches(0.9), Inches(0.4))
    _set(tb2.text_frame.paragraphs[0], str(num), 12, c, bold=True, align=PP_ALIGN.RIGHT)

def title_slide(title, subtitle, accent):
    s = new_slide()
    _rect(s, 0, 0, SW, SH, DARK_BLUE)
    _rect(s, 0, Inches(4.55), SW, Inches(0.06), accent)
    tb = _box(s, Inches(0.9), Inches(2.1), Inches(11.5), Inches(1.9))
    _set(tb.text_frame.paragraphs[0], title, 44, WHITE, bold=True)
    p = tb.text_frame.add_paragraph()
    _set(p, subtitle, 24, RGBColor(0xC9, 0xD6, 0xE8))
    tb2 = _box(s, Inches(0.9), Inches(4.9), Inches(11.5), Inches(0.6))
    _set(tb2.text_frame.paragraphs[0], "AGENT SCHOOL — COHORT 1", 18, accent, bold=True)
    return s

def section_slide(num_label, title, points, accent):
    s = new_slide()
    _rect(s, 0, 0, SW, SH, DARK_BLUE)
    tb = _box(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(1.6))
    _set(tb.text_frame.paragraphs[0], num_label, 22, accent, bold=True)
    p = tb.text_frame.add_paragraph()
    _set(p, title, 40, WHITE, bold=True)
    _rect(s, Inches(0.95), Inches(2.9), Inches(2.2), Inches(0.07), accent)
    tb2 = _box(s, Inches(0.9), Inches(3.4), Inches(11.3), Inches(3.2))
    tf = tb2.text_frame
    first = True
    for pt in points:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        _set(p, "•  " + pt, 20, RGBColor(0xDD, 0xE6, 0xF2), space_after=10)
    return s

def bullet_slide(title, bullets, accent, kicker=None):
    assert len(bullets) <= 6, "max 6 bullets: " + title
    s = new_slide()
    _rect(s, 0, 0, SW, SH, WHITE)
    _rect(s, Inches(0.55), Inches(0.55), Inches(0.14), Inches(0.85), accent)
    tb = _box(s, Inches(0.9), Inches(0.42), Inches(11.9), Inches(1.1))
    if kicker:
        p0 = tb.text_frame.paragraphs[0]
        _set(p0, kicker, 14, accent, bold=True)
        p = tb.text_frame.add_paragraph()
        _set(p, title, 30, DARK_BLUE, bold=True)
    else:
        _set(tb.text_frame.paragraphs[0], title, 32, DARK_BLUE, bold=True)
    body = _box(s, Inches(1.0), Inches(1.85), Inches(11.4), Inches(4.9))
    tf = body.text_frame
    first = True
    for b in bullets:
        if isinstance(b, tuple):
            txt, sub = b
        else:
            txt, sub = b, False
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        if sub:
            _set(p, "      –  " + txt, 18, GREY, space_after=8)
        else:
            _set(p, "•  " + txt, 20, RGBColor(0x22, 0x2B, 0x38), bold=False, space_after=12)
    return s

def demo_slide(title, lines, num):
    s = new_slide()
    _rect(s, 0, 0, SW, SH, DEEP_BLUE)
    _rect(s, 0, 0, SW, Inches(0.18), ORANGE)
    tb = _box(s, Inches(0.9), Inches(0.75), Inches(11.5), Inches(1.7))
    _set(tb.text_frame.paragraphs[0], "LIVE DEMO", 48, ORANGE, bold=True)
    p = tb.text_frame.add_paragraph()
    _set(p, title, 30, WHITE, bold=True)
    body = _box(s, Inches(1.0), Inches(2.9), Inches(11.3), Inches(3.6))
    tf = body.text_frame
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        _set(p, "•  " + ln, 20, RGBColor(0xE8, 0xEE, 0xF6), space_after=12)
    return s

def code_slide(title, code_lines, accent, kicker=None):
    s = new_slide()
    _rect(s, 0, 0, SW, SH, WHITE)
    _rect(s, Inches(0.55), Inches(0.55), Inches(0.14), Inches(0.85), accent)
    tb = _box(s, Inches(0.9), Inches(0.42), Inches(11.9), Inches(1.1))
    if kicker:
        _set(tb.text_frame.paragraphs[0], kicker, 14, accent, bold=True)
        p = tb.text_frame.add_paragraph()
        _set(p, title, 30, DARK_BLUE, bold=True)
    else:
        _set(tb.text_frame.paragraphs[0], title, 32, DARK_BLUE, bold=True)
    _rect(s, Inches(0.9), Inches(1.8), Inches(11.5), Inches(4.9), CODE_BG)
    body = _box(s, Inches(1.15), Inches(1.95), Inches(11.0), Inches(4.6))
    tf = body.text_frame
    first = True
    for ln in code_lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        _set(p, ln if ln else " ", 16, CODE_TX, font="Consolas", space_after=2)
    return s

S = []  # (slide, session_accent) built in order; footers applied at end

def reg(slide):
    S.append(slide)

# ================= SESSION 1 — WHAT AN AGENT REALLY IS (green) ================
A1 = GREEN
reg(title_slide("SESSION 1", "What an Agent Really Is — and why the next 4 Sundays will change how you work", A1))
reg(section_slide("SESSION 1 OF 4", "What an Agent Really Is",
    ["The promise: a working agent by Day 30", "AI vs Agent — brain + tools + loop",
     "Real examples you already use", "A LIVE demo on WhatsApp",
     "The anatomy, piece by piece", "Homework: your 3 wish-tasks"], A1))
reg(bullet_slide("The Promise of This Course", [
    "By Day 30 you will have a working agent of your own",
    "It will live where you already live: WhatsApp",
    "Zero-cost stack — no server bills while you learn",
    "Every class: concept, live demo, hands-on homework",
    "No prior coding needed — pseudocode first, code later",
    "If you do the homework, you cannot fail"], A1, kicker="SESSION 1 • THE DEAL"))
reg(bullet_slide("AI vs Agent — the Real Difference", [
    "AI (a chat) answers when you ask — then it sleeps",
    "An Agent has a goal and works until it is done",
    ("Brain: the model that reasons and decides", True),
    ("Tools: hands that send, read, search, calculate", True),
    ("Loop: think → act → observe → repeat until goal", True),
    "Chat = a consultant. Agent = an employee."], A1, kicker="SESSION 1 • CONCEPT"))
reg(bullet_slide("The Brain — the Model", [
    "The brain reads the goal and decides the next step",
    "It plans: what to do first, what to check after",
    "It writes the messages, summaries, and replies",
    "It does not act by itself — it only thinks",
    "Same brain, different tools = different jobs",
    "You will swap brains later without rebuilding"], A1, kicker="SESSION 1 • ANATOMY 1/3"))
reg(bullet_slide("The Tools — the Hands", [
    "A tool is a function the agent may call",
    "send_whatsapp(number, text) — it can talk",
    "read_file(path) — it can read your files",
    "search_web(query) — it can look things up",
    "Tools are what turn thinking into action",
    "Rule: give it only the tools the job needs"], A1, kicker="SESSION 1 • ANATOMY 2/3"))
reg(bullet_slide("The Loop — the Heartbeat", [
    "1. GOAL — what does 'done' look like?",
    "2. THINK — what is my next single step?",
    "3. ACT — call one tool",
    "4. OBSERVE — what came back? success or error?",
    "5. REPEAT — until the goal is met or I must stop",
    "The loop is why an agent feels alive"], A1, kicker="SESSION 1 • ANATOMY 3/3"))
reg(bullet_slide("Brain + Tools + Loop = Agent", [
    "Brain alone: a clever chatbot",
    "Tools alone: unused machinery",
    "Loop alone: a fan spinning in place",
    "Together: something that finishes work",
    "Every agent you will ever build is this recipe",
    "Master this picture — everything else is detail"], A1, kicker="SESSION 1 • THE FORMULA"))
reg(bullet_slide("Real Examples — You Already Met Agents", [
    "A customer-reply agent that answers at 2 AM",
    "A lead agent that follows up until it gets an answer",
    "A documents agent that reads invoices and fills sheets",
    "A booking agent that checks, compares, and confirms",
    "A reminder agent that nags politely and on time",
    "Same anatomy in all five — only tools differ"], A1, kicker="SESSION 1 • EXAMPLES"))
reg(bullet_slide("What Agents Are NOT", [
    "Not a human — it will make confident mistakes",
    "Not magic — it is a loop you can read and fix",
    "Not autonomous by default — YOU set the guardrails",
    "Not a replacement for judgment — it is a lever",
    "Not expensive — the stack in this course is zero-cost",
    "Not scary once you can see the loop"], A1, kicker="SESSION 1 • HONEST TALK"))
reg(bullet_slide("House Rules for the Live Demo", [
    "Nothing pre-recorded — what you see is what runs",
    "Shout a question; we will test it on the agent",
    "If it fails, we debug live — that is the lesson",
    "Screenshare covers WhatsApp Web and the agent console",
    "You may note timestamps; we will replay the log",
    "Demo starts in 5 minutes — questions now"], A1, kicker="SESSION 1 • BEFORE THE DEMO"))
reg(demo_slide("Your AI son answers on WhatsApp — screen shared, nothing pre-recorded",
    ["I send a real WhatsApp message to the agent, live",
     "You watch it think, act, and reply in real time",
     "We break one thing on purpose — and watch it recover",
     "Note the loop: my message → think → act → observe → reply",
     "Questions shouted out are tested live, right now"], 1))
reg(bullet_slide("What Just Happened in the Demo", [
    "Your message arrived — that was the trigger",
    "The brain read it and planned one step",
    "A tool did the work; the loop observed the result",
    "The reply you saw was chosen, not canned",
    "When the tool failed, the loop retried another path",
    "That is the whole trick — now you have seen it"], A1, kicker="SESSION 1 • DEMO DEBRIEF"))
reg(bullet_slide("Anatomy Recap — Say It Back", [
    "BRAIN — the model that reasons",
    "TOOLS — the functions that act",
    "LOOP — goal → think → act → observe → repeat",
    "TRIGGER — what wakes the agent up",
    "GUARDRAILS — the walls you build around it",
    "Next session: you build one, step by step"], A1, kicker="SESSION 1 • RECAP"))
reg(bullet_slide("Homework — Your 3 Wish-Tasks", [
    "Write 3 tasks you wish an agent did for you",
    "Make them concrete: who, what, when, how often",
    "Example: 'reply to price enquiries every evening 8 PM'",
    "For each, list what tools it would need",
    "Bring them next Sunday — S2 builds task #1 live",
    "Write them in the workbook, page 'Session 1'"], A1, kicker="SESSION 1 • HOMEWORK"))
reg(bullet_slide("Session 1 — In One Breath", [
    "An agent = brain + tools + loop",
    "A chat answers; an agent finishes",
    "You saw a real agent answer on WhatsApp, live",
    "You can name every part of the anatomy",
    "Homework: 3 wish-tasks, written, concrete",
    "Next: Build Your First Agent"], A1, kicker="SESSION 1 • CLOSE"))

# ================= SESSION 2 — BUILD YOUR FIRST AGENT (orange) ================
A2 = ORANGE
reg(title_slide("SESSION 2", "Build Your First Agent — the loop, the tools, the live build", A2))
reg(section_slide("SESSION 2 OF 4", "Build Your First Agent",
    ["The loop, step by step", "Tools are just functions",
     "LIVE BUILD: pseudocode on screen, together", "Prompt = instructions",
     "Guardrails: how not to get burned", "Homework: finish and run yours"], A2))
reg(bullet_slide("Recap in 60 Seconds", [
    "Agent = brain + tools + loop",
    "The brain thinks, the tools act, the loop repeats",
    "You wrote 3 wish-tasks for homework",
    "Today we build wish-task #1 together, live",
    "Everything today is pseudocode — plain English logic",
    "Copy the pattern; the code can come later"], A2, kicker="SESSION 2 • RECAP"))
reg(bullet_slide("The Loop — One More Time, Slower", [
    "GOAL → THINK → ACT → OBSERVE → REPEAT",
    "Every agent in the world runs some version of this",
    "The loop is boring — and that is the point",
    "Boring loops are debuggable loops",
    "If your agent misbehaves, you read the loop",
    "Today you write this loop with your own hands"], A2, kicker="SESSION 2 • THE LOOP"))
reg(bullet_slide("Loop Step — GOAL", [
    "A goal is a finish line, not a wish",
    "Bad goal: 'handle my customers'",
    "Good goal: 'reply to every unanswered price message'",
    "Write goals as: trigger + action + done-condition",
    "If you cannot say when it is done, it is not a goal",
    "The loop checks the goal after every step"], A2, kicker="SESSION 2 • LOOP 1/5"))
reg(bullet_slide("Loop Step — THINK", [
    "The brain asks: what is the next single step?",
    "It looks at the goal and what it has observed",
    "It picks one tool — never five at once",
    "It writes the exact inputs the tool needs",
    "Small steps are safe steps",
    "This is where prompts do their quiet work"], A2, kicker="SESSION 2 • LOOP 2/5"))
reg(bullet_slide("Loop Step — ACT", [
    "One tool call, with real inputs",
    "The act either works or fails — both are fine",
    "Failures are data, not disasters",
    "Never let one act delete or send irreversible things",
    "Irreversible acts need your approval (S3)",
    "Log every act — you will thank yourself"], A2, kicker="SESSION 2 • LOOP 3/5"))
reg(bullet_slide("Loop Step — OBSERVE", [
    "Read what the tool returned",
    "Success? Update progress toward the goal",
    "Error? Read it, adjust, try a different path",
    "The observation becomes the brain's next input",
    "Agents die when nobody reads the errors",
    "Observe honestly — do not assume success"], A2, kicker="SESSION 2 • LOOP 4/5"))
reg(bullet_slide("Loop Step — REPEAT (and when to STOP)", [
    "Repeat until the goal's done-condition is true",
    "Always set a max: N steps or T minutes",
    "No stop-condition = infinite loop = chaos",
    "If stuck twice: stop and ask a human",
    "'Ask a human' is also a tool",
    "Stopping well is a skill, not a failure"], A2, kicker="SESSION 2 • LOOP 5/5"))
reg(bullet_slide("Tools Are Just Functions", [
    "function = name + inputs + output",
    "send_whatsapp(number, text) → message_id",
    "read_file(path) → text",
    "search_web(query) → results",
    "add_note(title, body) → saved",
    "If you can write the name and inputs, you can design a tool"], A2, kicker="SESSION 2 • TOOLS"))
reg(bullet_slide("Designing a Tool — the Checklist", [
    "ONE job per tool — do not build a Swiss knife",
    "Name it as a verb: send_, read_, search_, add_",
    "Inputs must be simple: text, number, path",
    "Output must be readable by the brain",
    "Decide its failure story: what does it return on error?",
    "You will reuse tools across every future agent"], A2, kicker="SESSION 2 • TOOLS"))
reg(code_slide("LIVE BUILD — What We Are Building",
    ["AGENT: 'Evening Reply Bot'",
     "", "GOAL: every unanswered price enquiry gets a",
     "      polite reply the same evening",
     "TRIGGER: 8:00 PM daily",
     "TOOLS: read_messages(), reply_whatsapp(),",
     "       log_sheet(), ask_human()",
     "GUARDRAILS: never quote discounts, never promise",
     "      dates — escalate those to a human"], A2, kicker="SESSION 2 • LIVE BUILD"))
reg(code_slide("LIVE BUILD — Pseudocode 1: the Skeleton",
    ["agent = Agent(",
     "    brain  = model(),",
     "    prompt = INSTRUCTIONS,",
     "    tools  = [read_messages, reply_whatsapp,",
     "              log_sheet, ask_human],",
     "    stop   = max_steps(10)",
     ")",
     "", "# That's it. Everything else is detail",
     "# inside the loop."], A2, kicker="SESSION 2 • LIVE BUILD"))
reg(code_slide("LIVE BUILD — Pseudocode 2: the Loop",
    ["while not goal_done and steps < 10:",
     "    step   = brain.think(goal, history)",
     "    result = act(step.tool, step.inputs)",
     "    history.append(observe(result))",
     "", "    if result looks wrong:",
     "        history.append(ask_human(result))",
     "", "log_sheet.write('done:', goal_done)"], A2, kicker="SESSION 2 • LIVE BUILD"))
reg(code_slide("LIVE BUILD — Pseudocode 3: the Prompt",
    ["INSTRUCTIONS = '''",
     "You are Evening Reply Bot for <business>.",
     "Goal: reply to unanswered price enquiries.",
     "Tone: warm, short, human. Bengali or English",
     "as the customer used.",
     "NEVER: discounts, dates, promises, legal talk.",
     "If asked for those → ask_human().",
     "Always log every reply with log_sheet().",
     "'''"], A2, kicker="SESSION 2 • LIVE BUILD"))
reg(bullet_slide("Prompt = Instructions — Write Like a Boss", [
    "The prompt is the agent's job description",
    "Say WHO it is, WHAT the goal is, HOW to speak",
    "List the NEVERs as hard rules, not hints",
    "Give one worked example inside the prompt",
    "Short prompts beat essays — clarity beats length",
    "Rewrite the prompt whenever behaviour is wrong"], A2, kicker="SESSION 2 • PROMPTS"))
reg(bullet_slide("Guardrails — How Not to Get Burned", [
    "Scope lock: only the tools this job needs",
    "Step cap: max 10 steps, then stop",
    "Human gate: irreversible acts need approval",
    "No secrets in prompts — keys stay in config",
    "Dry-run mode: rehearse before it touches reality",
    "A safe agent is a boring agent — keep it boring"], A2, kicker="SESSION 2 • GUARDRAILS"))
reg(bullet_slide("Homework — Session 2", [
    "Take wish-task #1 from your S1 homework",
    "Write its GOAL in trigger + action + done form",
    "List its tools (names + inputs + outputs)",
    "Write its 8–12 line instruction prompt",
    "Write the loop pseudocode — copy today's pattern",
    "Bring it Sunday: S3 puts it on WhatsApp"], A2, kicker="SESSION 2 • HOMEWORK"))
reg(bullet_slide("Session 2 — In One Breath", [
    "GOAL → THINK → ACT → OBSERVE → REPEAT",
    "Tools are functions with one job each",
    "You wrote a full agent in pseudocode today",
    "The prompt is the boss's voice — write it clearly",
    "Guardrails make agents safe and boring",
    "Next: Agents on WhatsApp"], A2, kicker="SESSION 2 • CLOSE"))

# ================= SESSION 3 — AGENTS ON WHATSAPP (green) =====================
A3 = GREEN
reg(title_slide("SESSION 3", "Agents on WhatsApp — where India lives, your agent works", A3))
reg(section_slide("SESSION 3 OF 4", "Agents on WhatsApp",
    ["WhatsApp = where India lives", "The zero-cost stack",
     "Architecture: WhatsApp Web → bridge → agent → tools", "LIVE DEMO: end to end",
     "Safety: identity, pacing, human approval", "Homework: connect yours"], A3))
reg(bullet_slide("Recap in 60 Seconds", [
    "You wrote goal, tools, loop, and prompt",
    "Your agent exists — on paper",
    "Today it gets a body: WhatsApp",
    "Zero-cost stack — nothing to buy today",
    "You will see the full round trip, live",
    "Bring your homework — you will map it today"], A3, kicker="SESSION 3 • RECAP"))
reg(bullet_slide("WhatsApp = Where India Lives", [
    "500M+ Indians open it every single day",
    "Your customer, your uncle, your supplier — all there",
    "No app install, no onboarding, no training",
    "Messages feel personal — replies get read",
    "An agent on WhatsApp works where attention already is",
    "That is distribution most startups dream of"], A3, kicker="SESSION 3 • WHY WHATSAPP"))
reg(bullet_slide("Why Not Build an App Instead?", [
    "Apps cost money: hosting, updates, store reviews",
    "Apps need install — the death step for users",
    "WhatsApp needs nothing new from your user",
    "Your agent ships in days, not months",
    "Later, an app can come — later",
    "First make something people already use"], A3, kicker="SESSION 3 • WHY WHATSAPP"))
reg(bullet_slide("The Zero-Cost Stack — Today's Ingredients", [
    "WhatsApp Web — the surface you already know",
    "An MCP bridge — connects WhatsApp to the agent",
    "The agent core — your S2 loop + prompt",
    "Tools — read_messages, reply, log, ask_human",
    "Your laptop — the whole thing runs on it",
    "Total cost today: zero rupees"], A3, kicker="SESSION 3 • STACK"))
reg(bullet_slide("Architecture — the Full Round Trip", [
    "1. Customer's message lands on WhatsApp",
    "2. WhatsApp Web mirrors it to your machine",
    "3. The MCP bridge hands it to the agent",
    "4. The agent loop: think → act → observe",
    "5. Reply travels back through the same bridge",
    "6. Customer sees a reply — seconds later"], A3, kicker="SESSION 3 • ARCHITECTURE"))
reg(bullet_slide("Architecture — the Bridge, Piece by Piece", [
    "The bridge watches WhatsApp Web for new messages",
    "It converts each message into a clean event",
    "It passes the event to the agent core",
    "It takes the agent's reply and sends it back",
    "It also logs everything for your review",
    "Bridge = postman: it carries, never decides"], A3, kicker="SESSION 3 • ARCHITECTURE"))
reg(bullet_slide("Architecture — the Agent Core", [
    "Receives the event: who wrote, what they wrote",
    "Loads your prompt — its job description",
    "Thinks: is a reply needed? what should it say?",
    "Acts through tools — reply, log, or ask_human",
    "Observes the result of every act",
    "Same loop from S2 — nothing new to learn"], A3, kicker="SESSION 3 • ARCHITECTURE"))
reg(bullet_slide("Choosing Your Agent's Personality", [
    "Name it — agents with names get better prompts",
    "Voice: warm and short, like a trusted assistant",
    "Language: mirror the customer — Bengali or English",
    "Boundaries: it never promises, never negotiates",
    "Signature: how it introduces itself, once",
    "Personality is a prompt decision, not a vibe"], A3, kicker="SESSION 3 • PERSONALITY"))
reg(bullet_slide("Setup Walkthrough — Before the Demo", [
    "Step 1: WhatsApp Web linked on the host laptop",
    "Step 2: bridge started, watching for new messages",
    "Step 3: agent core loaded with prompt + tools",
    "Step 4: test message from a second phone",
    "Step 5: console shows trigger → think → act",
    "Five steps, five minutes, zero installs for you"], A3, kicker="SESSION 3 • SETUP"))
reg(demo_slide("End to end, live: a customer writes → your agent answers → logs the reply",
    ["A real number sends a real price enquiry",
     "The bridge fires; the agent thinks on screen",
     "You see the tool call and the reply drafted",
     "Reply lands back on the customer's WhatsApp",
     "We flip on 'ask_human' — watch it escalate a discount ask",
     "Then we break the bridge — and watch the failure surface"], 3))
reg(bullet_slide("What to Watch in the Demo", [
    "The trigger: how fast the bridge notices",
    "The think step: the agent's plan, out loud",
    "The act: one tool, clean inputs",
    "The observe: what came back, and what it did next",
    "The escalate: ask_human firing at the right time",
    "Sketch this flow in your workbook now"], A3, kicker="SESSION 3 • DEMO DEBRIEF"))
reg(bullet_slide("Safety 1 — Identity Rules", [
    "The agent says it is an assistant — never a human",
    "It introduces itself once, clearly, by name",
    "Never uses your personal photo as its avatar",
    "Never claims feelings, health, or family emergencies",
    "One identity, consistent everywhere",
    "Trust is the product — do not counterfeit it"], A3, kicker="SESSION 3 • SAFETY"))
reg(bullet_slide("Safety 2 — Pacing", [
    "No reply storms: one reply per customer message",
    "Night mode: the agent sleeps when you sleep",
    "Rate limit: max N messages per minute, hard-coded",
    "New contacts: slower, gentler first touches",
    "No broadcasts to strangers — ever",
    "Calm agents keep their numbers alive"], A3, kicker="SESSION 3 • SAFETY"))
reg(bullet_slide("Safety 3 — Human Approval", [
    "Irreversible acts need a human yes: payments, promises",
    "Discounts, dates, refunds, commitments → ask_human",
    "The approval lands on YOUR WhatsApp — one tap",
    "No answer in 15 minutes → agent waits, does not guess",
    "Approval log reviewed weekly",
    "You are the boss; the agent knows it"], A3, kicker="SESSION 3 • SAFETY"))
reg(bullet_slide("Common Failure Modes — and the Fix", [
    "Agent loops forever → step cap + stop conditions",
    "Replies feel robotic → rewrite prompt with examples",
    "Bridge misses messages → check WhatsApp Web login",
    "Agent hallucinates prices → give it a price tool",
    "Too many tool calls → one job per tool, stricter prompt",
    "Every failure is a prompt or a tool, not a mystery"], A3, kicker="SESSION 3 • TROUBLESHOOTING"))
reg(bullet_slide("Homework — Session 3", [
    "Map YOUR wish-task onto this architecture",
    "Write its trigger: what wakes it up?",
    "List its guardrails: NEVERs, caps, human gates",
    "Draft its first message (identity intro, 2 lines)",
    "Sketch the round trip for your task in the workbook",
    "Next Sunday: we ship it and talk money"], A3, kicker="SESSION 3 • HOMEWORK"))
reg(bullet_slide("Session 3 — In One Breath", [
    "WhatsApp is distribution you already own",
    "Bridge carries; the agent decides",
    "Zero-cost stack runs on your laptop",
    "Identity, pacing, approval — the three safety walls",
    "You saw the full round trip, live",
    "Next: Ship It & Earn"], A3, kicker="SESSION 3 • CLOSE"))

# ================= SESSION 4 — SHIP IT & EARN (orange) ========================
A4 = ORANGE
reg(title_slide("SESSION 4", "Ship It & Earn — deployment, cost truth, and your first income", A4))
reg(section_slide("SESSION 4 OF 4", "Ship It & Earn",
    ["Deployment: laptop → always-on", "Cost truth: zero-cost vs API",
     "Three ways to earn from agents", "Certificates + next cohort",
     "Your 30-day map, reviewed", "Stay hungry, stay foolish"], A4))
reg(bullet_slide("Recap — the Journey So Far", [
    "S1: what an agent is — brain + tools + loop",
    "S2: you built one in pseudocode",
    "S3: you put it on WhatsApp, safely",
    "S4 today: make it run without you — and earn",
    "You are 4 Sundays in and past most people",
    "Today is about finishing"], A4, kicker="SESSION 4 • RECAP"))
reg(bullet_slide("Deployment — From Laptop to Always-On", [
    "Stage 1: your laptop (learning — fine for now)",
    "Stage 2: an old machine at home, always plugged",
    "Stage 3: a tiny free-tier cloud box, when earning",
    "Deployment = agent + bridge running headless",
    "Add a watchdog: if it dies, it restarts itself",
    "Ship stage 2 this week — stage 3 when a client pays"], A4, kicker="SESSION 4 • DEPLOY"))
reg(bullet_slide("Deployment Checklist — Before You Call It Shipped", [
    "Restarts on its own after a crash",
    "Logs to a file you actually read",
    "Step caps and human gates still ON",
    "You can pause it with one command",
    "A friend tested it and could not break it",
    "If all six tick: it is shipped"], A4, kicker="SESSION 4 • DEPLOY"))
reg(bullet_slide("Cost Truth — the Zero-Cost Stack", [
    "WhatsApp Web route: zero rupees in tooling",
    "Runs on hardware you already own",
    "Free-tier model access while you learn",
    "True cost: your time — spend it on prompts and tools",
    "Perfect for learning and first clients",
    "Know its limits: one number, one machine"], A4, kicker="SESSION 4 • COST"))
reg(bullet_slide("Cost Truth — When APIs Enter", [
    "Official APIs cost per message and per token",
    "They buy: scale, reliability, higher limits",
    "Rule: pay only when a paying client needs it",
    "One client's fees should fit inside their fee to you",
    "Track cost per conversation from day one",
    "Never subsidise a client's volume from your pocket"], A4, kicker="SESSION 4 • COST"))
reg(bullet_slide("When to Pay and When Not To", [
    "Learning → zero-cost, always",
    "First 1–2 clients → still zero-cost if it holds",
    "A client with real volume → API, billed to them",
    "Boring reliability problem → pay for boring reliability",
    "Never pay for shiny — pay for stuck",
    "Cost review every month, on the calendar"], A4, kicker="SESSION 4 • COST"))
reg(bullet_slide("Earn 1 — Freelance: Build Agents for Others", [
    "Small businesses drown in repetitive WhatsApp work",
    "Offer: 'I build a reply agent for your business'",
    "Deliverable: one agent, one trigger, three guardrails",
    "First gig: do it cheap or free for a testimonial",
    "Second gig onward: charge properly",
    "Your S2–S3 homework is literally the portfolio"], A4, kicker="SESSION 4 • EARN"))
reg(bullet_slide("Earn 2 — Business Automation: Agent-in-Residence", [
    "Your own shop, firm, or family business first",
    "Automate: enquiries, follow-ups, reminders, records",
    "Measure hours saved per week — write it down",
    "Hours saved = money you can now go earn elsewhere",
    "This is your testing ground with zero pressure",
    "Every saved hour becomes a case study"], A4, kicker="SESSION 4 • EARN"))
reg(bullet_slide("Earn 3 — Agent-as-a-Service: Monthly Income", [
    "You keep the agent running; client pays monthly",
    "Offer: setup fee + monthly care (updates, logs, fixes)",
    "Ten small clients beat one big gamble",
    "Contracts: scope, response time, what is NEVER included",
    "Renewal is the real business — care well",
    "This is how one agent becomes a salary"], A4, kicker="SESSION 4 • EARN"))
reg(bullet_slide("Pricing Your First Gig", [
    "Price the outcome, not your hours",
    "Ask: how many hours does this task eat monthly?",
    "Starter band: setup fee + small monthly care",
    "Under-price once for the testimonial — once only",
    "Raise price with every third client",
    "Never compete to the bottom — compete on trust"], A4, kicker="SESSION 4 • EARN"))
reg(bullet_slide("Finding Your First Three Clients", [
    "Client 1: a business you already know — family, friend",
    "Client 2: their referral — ask for it explicitly",
    "Client 3: your local market — one honest demo",
    "Lead with the demo, not the technology",
    "'Watch it answer' closes; slides do not",
    "Your WhatsApp demo from S3 is the whole pitch"], A4, kicker="SESSION 4 • EARN"))
reg(bullet_slide("Certificates — Cohort 1", [
    "Certificate = you attended + you shipped",
    "Attendance: all 4 sessions or watched recordings",
    "Shipping: your agent ran and did one real task",
    "Submit: goal, tools list, prompt, one screenshot",
    "Certificates carry the cohort date and your name",
    "This is a portfolio piece, not a participation trophy"], A4, kicker="SESSION 4 • CLOSE"))
reg(bullet_slide("Your 30-Day Map — Reviewed", [
    "Week 1: anatomy + 3 wish-tasks (done)",
    "Week 2: build in pseudocode (done)",
    "Week 3: WhatsApp + safety (done)",
    "Week 4: ship + first client conversation (now)",
    "Day 30: one working agent, one real user, one invoice",
    "Print this page; tick boxes as you go"], A4, kicker="SESSION 4 • CLOSE"))
reg(bullet_slide("Next Cohort — What Changes", [
    "Cohort 2 goes deeper: real code, real APIs",
    "New sessions: multi-agent teams, memory, evaluation",
    "Cohort 1 graduates get the alumni rate",
    "Refer a paying student — earn your first referral fee",
    "Teaching what you learned cements it — come assist",
    "The school grows only if you grow"], A4, kicker="SESSION 4 • CLOSE"))
reg(bullet_slide("Stay Hungry, Stay Foolish", [
    "You started with a wish-list; you leave with an agent",
    "The loop you learned builds more than software",
    "Goal → think → act → observe → repeat — run YOUR week on it",
    "Ship weekly. Talk to users. Fix what breaks.",
    "The next tool will change; the anatomy will not",
    "Stay hungry. Stay foolish."], A4, kicker="SESSION 4 • CLOSE"))
reg(title_slide("THANK YOU", "AGENT SCHOOL — COHORT 1 · You are now the person who builds agents", A4))

# footers + slide numbers
for i, s in enumerate(S, start=1):
    dark = True
    for shp in s.shapes:
        if shp.has_text_frame and shp.text_frame.text.strip() and shp.left is not None and shp.top is not None:
            pass
    # decide darkness by checking our known builders: title/section/demo have a full-bleed first rect
    full_bleed = False
    for shp in s.shapes:
        if shp.shape_type is not None and shp.width == SW and shp.height == SH:
            full_bleed = True
            break
    footer(s, i, dark=full_bleed)

prs.save(OUT)
print("SAVED", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
