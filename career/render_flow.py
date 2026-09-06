"""Render the WhatsApp MCP -> Agent architecture flow diagram locally.
Pure PIL drawing, white background, 1400x1000. No internet image APIs.
Output: D:\\anonym\\career\\mcp_agent_flow.png
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1400, 1000
WHITE = (255, 255, 255)
INK = (17, 24, 39)
GRAY = (75, 85, 99)
DARK = (31, 41, 55)       # WhatsApp layer
DARK_BR = (17, 24, 39)
BLUE = (29, 78, 216)      # MCP bridge
BLUE_BR = (30, 58, 138)
GREEN = (21, 128, 61)     # agent core
GREEN_BR = (20, 83, 45)
ORANGE = (234, 88, 12)    # tool belt
ORANGE_BR = (124, 45, 18)
MAROON = (124, 45, 18)    # guardrails
MAROON_BR = (67, 20, 7)
BODY_TXT = (243, 244, 246)


def font(bold, size):
    names = ("arialbd.ttf", "arial.ttf") if bold else ("arial.ttf", "arialbd.ttf")
    for name in names:
        path = os.path.join("C:/Windows/Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)

F_TITLE = font(True, 30)
F_SUB = font(False, 17)
F_BOX = font(True, 18)
F_BODY = font(False, 15)
F_LBL = font(True, 14)
F_FOOT = font(False, 13)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def box(x1, y1, x2, y2, fill, border, title, body):
    d.rounded_rectangle([x1, y1, x2, y2], radius=14, fill=fill,
                        outline=border, width=3)
    tw = d.textlength(title, font=F_BOX)
    d.text(((x1 + x2) / 2 - tw / 2, y1 + 12), title, font=F_BOX, fill=WHITE)
    yy = y1 + 38
    for line in wrap(body, F_BODY, (x2 - x1) - 32):
        d.text((x1 + 16, yy), line, font=F_BODY, fill=BODY_TXT)
        yy += 19


def line_arrow(x1, y1, x2, y2, color=INK, width=4):
    d.line([x1, y1, x2, y2], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    length, spread = 14, math.radians(24)
    p1 = (x2 - length * math.cos(ang - spread), y2 - length * math.sin(ang - spread))
    p2 = (x2 - length * math.cos(ang + spread), y2 - length * math.sin(ang + spread))
    d.polygon([(x2, y2), p1, p2], fill=color)


def dash(x1, y1, x2, y2, color, width=3, dash_len=9, gap=7):
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    t = 0.0
    while t < length:
        end = min(t + dash_len, length)
        d.line([x1 + ux * t, y1 + uy * t, x1 + ux * end, y1 + uy * end],
               fill=color, width=width)
        t += dash_len + gap


# ---- Title ----
title = "WhatsApp MCP -> Agent Architecture: the Zero-Cost Production Fortress"
tw = d.textlength(title, font=F_TITLE)
d.text((W / 2 - tw / 2, 22), title, font=F_TITLE, fill=INK)
sub = ("session-based MCP control of a real browser  ·  no WhatsApp Business API  ·  "
       "no crawling  ·  Rs 0 per month")
sw = d.textlength(sub, font=F_SUB)
d.text((W / 2 - sw / 2, 62), sub, font=F_SUB, fill=GRAY)

# ---- Row 1: WhatsApp layer (dark) ----
bw, gap = 400, 40
y1, y2 = 100, 232
box(60, y1, 60 + bw, y2, DARK, DARK_BR, "PAIRED PHONE",
    "QR scanned once; the session stays alive. The session is the licence - "
    "no vendor account, no fees.")
box(60 + bw + gap, y1, 60 + 2 * bw + gap, y2, DARK, DARK_BR,
    "WHATSAPP WEB IN CHROME",
    "One real browser, one real account. Chats are ordinary DOM - visible, "
    "clickable, automatable.")
box(60 + 2 * (bw + gap), y1, 1340, y2, DARK, DARK_BR, "ONE INBOX, ALL TRAFFIC",
    "Recruiter replies, KDP alerts, family threads - everything flows through "
    "this single pane.")

# arrows row1 <-> row2
line_arrow(600, 232, 600, 296)
line_arrow(800, 300, 800, 236)
lw = d.textlength("in: messages surface as DOM", font=F_LBL)
d.text((588 - lw, 248), "in: messages surface as DOM", font=F_LBL, fill=INK)
d.text((814, 248), "out: replies typed and sent", font=F_LBL, fill=INK)

# ---- Row 2: MCP bridge (blue) ----
box(60, 300, 1340, 412, BLUE, BLUE_BR,
    "MCP BRIDGE  -  chrome-devtools MCP over CDP",
    "Reads the DOM, clicks, types, screenshots. Exposes clean tools to the agents: "
    "read_inbox / send_message / check_thread. The browser itself is the API - "
    "nothing between agent and WhatsApp but the logged-in session.")

# arrows row2 <-> row3
line_arrow(600, 412, 600, 476)
line_arrow(800, 480, 800, 416)
lw = d.textlength("tool calls: read_inbox, state", font=F_LBL)
d.text((588 - lw, 428), "tool calls: read_inbox, state", font=F_LBL, fill=INK)
d.text((814, 428), "results: drafts, decisions", font=F_LBL, fill=INK)

# ---- Row 3: Agent core (green) ----
box(60, 480, 60 + bw, 612, GREEN, GREEN_BR, "INTENT DETECTOR",
    "What is this message? Job reply, KDP update, family note, or something "
    "that must go to Kunal.")
box(60 + bw + gap, 480, 60 + 2 * bw + gap, 612, GREEN, GREEN_BR, "MEMORY",
    "Identity rules, project state, past promises. The agent knows what was "
    "said to whom, and when.")
box(60 + 2 * (bw + gap), 480, 1340, 612, GREEN, GREEN_BR, "REPLY DRAFTER",
    "Writes in Kunal's own voice: short, warm, precise. Pacing law built in - "
    "pairs, then pause.")

# arrow row3 -> row4
line_arrow(700, 612, 700, 676)
d.text((714, 626), "approved sends only", font=F_LBL, fill=INK)

# ---- Row 4: Tool belt (orange) ----
bw4, g4 = 302, 24
y3, y4 = 680, 812
box(60, y3, 60 + bw4, y4, ORANGE, ORANGE_BR, "WHATSAPP SEND",
    "Replies and acknowledgements go back into the same session - no second "
    "number, no API bill.")
box(60 + bw4 + g4, y3, 60 + 2 * bw4 + g4, y4, ORANGE, ORANGE_BR, "JOB BOARDS",
    "Naukri, Foundit, LinkedIn: search, apply, follow up on schedule.")
box(60 + 2 * (bw4 + g4), y3, 60 + 3 * bw4 + 2 * g4, y4, ORANGE, ORANGE_BR,
    "KDP + FILES",
    "Book status, covers, reports, whole-arc manuscript work.")
box(60 + 3 * (bw4 + g4), y3, 1340, y4, ORANGE, ORANGE_BR, "ESCALATE TO KUNAL",
    "Sensitive or unsure? The agent stops and asks the human. Yes or no, "
    "then it acts.")

# ---- Guardrails bar (maroon) ----
dash(350, 812, 350, 858, MAROON)
dash(1050, 812, 1050, 858, MAROON)
box(60, 862, 1340, 962, MAROON, MAROON_BR,
    "GUARDRAILS  -  THE LAW EVERY LAYER OBEYS",
    "Identity: books ship as NILOY DAS, never the personal name. Pacing: no message "
    "bursts - pairs, then pause. Messaging only: no calls, no video. Human approval "
    "on every sensitive send. No crawling - the logged-in session is the only door in.")

# ---- Footer ----
foot = "drawn locally with Python/PIL - no internet image APIs  ·  Beholder stack  ·  2026-09-06"
fw = d.textlength(foot, font=F_FOOT)
d.text((W - 24 - fw, 972), foot, font=F_FOOT, fill=GRAY)

out = r"D:\anonym\career\mcp_agent_flow.png"
img.save(out)
print("saved", out, os.path.getsize(out), "bytes")
