# -*- coding: utf-8 -*-
"""AGENT SCHOOL - COHORT 1 : STUDENT-WORKBOOK.pdf (10-12 pages)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak, KeepTogether)

OUT = r"D:\anonym\career\agent-school\STUDENT-WORKBOOK.pdf"

DARK_BLUE = HexColor("#152C51")
GREEN     = HexColor("#1E9E6A")
ORANGE    = HexColor("#F39C12")
GREY      = HexColor("#5A6473")
LIGHT     = HexColor("#F5F7FA")
INK       = HexColor("#222B38")
RULE      = HexColor("#B9C4D6")

PW, PH = A4
M = 1.9 * cm

st_h1   = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=DARK_BLUE, spaceAfter=4)
st_h2   = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=DARK_BLUE, spaceBefore=10, spaceAfter=5)
st_h2g  = ParagraphStyle("h2g", parent=st_h2, textColor=GREEN)
st_h2o  = ParagraphStyle("h2o", parent=st_h2, textColor=HexColor("#C87F06"))
st_body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=5)
st_kick = ParagraphStyle("kick", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=GREEN, spaceAfter=2)
st_kicko= ParagraphStyle("kicko", parent=st_kick, textColor=ORANGE)
st_li   = ParagraphStyle("li", parent=st_body, leftIndent=14, bulletIndent=4, spaceAfter=3)
st_code = ParagraphStyle("code", fontName="Courier", fontSize=9.5, leading=13.5, textColor=HexColor("#9CE3B0"), backColor=HexColor("#101828"), borderPadding=6, leftIndent=4, rightIndent=4, spaceBefore=6, spaceAfter=6)
st_note = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=9.5, leading=13, textColor=GREY, spaceAfter=4)
st_cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
st_cellb= ParagraphStyle("cellb", parent=st_cell, fontName="Helvetica-Bold")

def lines(n=1):
    return Spacer(1, 16 * n)

def box_table(rows, colw, header=None):
    data = []
    if header:
        data.append([Paragraph(h, st_cellb) for h in header])
    for r in rows:
        data.append([Paragraph(c, st_cell) for c in r])
    t = Table(data, colWidths=colw)
    style = [("GRID", (0, 0), (-1, -1), 0.75, RULE),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 6),
             ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE)]
        for c in range(len(header)):
            data[0][c].style.textColor = white
    t.setStyle(TableStyle(style))
    return t

def write_zone(n=8, label="Write here:"):
    tbl = Table([[Paragraph(label, st_note)]] + [[""] * 1 for _ in range(n)], colWidths=[PW - 2 * M - 1 * cm], rowHeights=[None] + [0.85 * cm] * n)
    tbl.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.75, RULE),
                             ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    return tbl

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(M, 1.35 * cm, PW - M, 1.35 * cm)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(GREY)
    canvas.drawString(M, 1.0 * cm, "AGENT SCHOOL — COHORT 1 · STUDENT WORKBOOK")
    canvas.drawRightString(PW - M, 1.0 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=1.7 * cm, bottomMargin=1.9 * cm, title="Agent School Cohort 1 — Student Workbook", author="AGENT SCHOOL")
frame = Frame(M, 1.9 * cm, PW - 2 * M, PH - 3.6 * cm, id="main")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

E = []

# ---------- PAGE 1 : COVER ----------
E.append(Spacer(1, 2.2 * cm))
E.append(Paragraph("AGENT SCHOOL", ParagraphStyle("cov", fontName="Helvetica-Bold", fontSize=40, leading=46, textColor=DARK_BLUE)))
E.append(Paragraph("STUDENT WORKBOOK", ParagraphStyle("cov2", fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=GREEN)))
E.append(Spacer(1, 0.4 * cm))
E.append(Paragraph("COHORT 1 · 4 Sessions · Build one working agent by Day 30", st_body))
E.append(Spacer(1, 0.8 * cm))
t = Table([["NAME", ""], ["PHONE / WHATSAPP", ""], ["SESSION DATES", "S1 ____   S2 ____   S3 ____   S4 ____"], ["MY AGENT'S NAME", ""]], colWidths=[5.5 * cm, PW - 2 * M - 5.5 * cm], rowHeights=[0.9 * cm] * 4)
t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.75, RULE), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
E.append(t)
E.append(Spacer(1, 0.6 * cm))
E.append(Paragraph("Bring this workbook to every session. Every homework page is designed to be filled in by hand — the act of writing is part of the course.", st_note))
E.append(PageBreak())

# ---------- PAGE 2 : GLOSSARY ----------
E.append(Paragraph("GLOSSARY — the six words that matter", st_h1))
E.append(Paragraph("Session 1 · Learn these before Session 2", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table(
    [["AGENT", "A program with a GOAL that runs a LOOP: it thinks, uses tools, observes the result, and repeats until the goal is done. A chat answers; an agent finishes."],
     ["TOOL", "A function the agent may call, with one job: send_whatsapp(number, text), read_file(path), search_web(query). Tools turn thinking into action."],
     ["LOOP", "The heartbeat: GOAL → THINK → ACT → OBSERVE → REPEAT, with a stop condition (max steps or max time) so it can never run away."],
     ["PROMPT", "The agent's job description, written by you: who it is, what its goal is, how it speaks, and the hard NEVERs. The first thing to fix when behaviour is wrong."],
     ["GUARDRAIL", "The walls around the agent: scope lock (few tools), step cap, human approval for irreversible acts, no secrets in prompts, dry-run mode."],
     ["MCP", "Model Context Protocol — a standard way to connect an agent to tools and data sources. Our WhatsApp bridge speaks MCP: it carries messages, never decides."]],
    [3.6 * cm, PW - 2 * M - 3.6 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph("Say it back: an agent is BRAIN + TOOLS + LOOP with GUARDRAILS, told what to do by a PROMPT, connected to the world through MCP.", ParagraphStyle("sayback", fontName="Helvetica-BoldOblique", fontSize=10.5, leading=15, textColor=GREEN)))
E.append(PageBreak())

# ---------- PAGE 3 : GLOSSARY WORKSHEET ----------
E.append(Paragraph("GLOSSARY WORKSHEET", st_h1))
E.append(Paragraph("Session 1 · Fill from memory, then check the previous page", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table([["AGENT", "In your own words:"], ["TOOL", "Name 3 tools you would give a shop-reply agent:"], ["LOOP", "Write the 5 steps in order:"], ["PROMPT", "What belongs in a prompt? Name 3 things:"], ["GUARDRAIL", "Name 3 guardrails:"], ["MCP", "What does the bridge do — and what does it never do?"]], [3.6 * cm, PW - 2 * M - 3.6 * cm]))
E.append(lines(1))
E.append(Paragraph("The one-sentence test", st_h2))
E.append(Paragraph("Write ONE sentence that would explain to your family what you are building this month:", st_body))
E.append(write_zone(3, ""))
E.append(PageBreak())

# ---------- PAGE 4 : 5 PROMPT TEMPLATES ----------
E.append(Paragraph("5 COPY-PASTE PROMPT TEMPLATES", st_h1))
E.append(Paragraph("Session 2 · Replace anything in ⟨angle brackets⟩. Keep every NEVER line.", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(Paragraph("Template 1 — Customer Reply Agent", st_h2o))
E.append(Paragraph("You are ⟨Name⟩, the assistant for ⟨business⟩.<br/>Goal: reply to every unanswered ⟨enquiry/support⟩ message the same evening.<br/>Tone: warm, short, human. Mirror the customer's language (Bengali or English).<br/>NEVER: discounts, delivery dates, promises, legal or medical advice.<br/>If asked for those → use ask_human().<br/>Log every reply with log_sheet().", st_code))
E.append(Paragraph("Template 2 — Follow-up Agent", st_h2o))
E.append(Paragraph("You are ⟨Name⟩, follow-up assistant for ⟨business⟩.<br/>Goal: follow up on unanswered quotes until a clear yes/no, max 3 touches, 2 days apart.<br/>Tone: polite, brief, never pushy.<br/>NEVER: more than one message per day per person, never after 9 PM.<br/>If no reply after 3 touches → mark COLD and stop.<br/>Log every touch with log_sheet().", st_code))
E.append(Paragraph("Template 3 — Records & Reminders Agent", st_h2o))
E.append(Paragraph("You are ⟨Name⟩, records assistant for ⟨business/family⟩.<br/>Goal: at ⟨time⟩ daily, read today's entries and send reminders for ⟨events/payments/doses⟩ due.<br/>Tone: one line per reminder, friendly.<br/>NEVER: invent amounts or dates — read them from the file, or ask_human().<br/>If the file is missing → message me, wait for instructions.", st_code))
E.append(Paragraph("Template 4 — Research & Summarise Agent", st_h2o))
E.append(Paragraph("You are ⟨Name⟩, my research assistant.<br/>Goal: when I send a topic, search the web (max 5 searches), then reply with a 10-line summary and source links.<br/>Tone: plain language, no jargon.<br/>NEVER: guess — if sources disagree, show both.<br/>Always end with: 'Want the full notes?'", st_code))
E.append(Paragraph("Template 5 — Personal Assistant Agent", st_h2o))
E.append(Paragraph("You are ⟨Name⟩, my personal assistant on this number.<br/>Goal: take my voice/text notes and reminders, and at ⟨time⟩ send me tomorrow's list.<br/>Tone: how I speak — short, no emoji.<br/>NEVER: message anyone except me, never delete anything, never share my notes.<br/>If a request is unclear → ask me one question.", st_code))
E.append(PageBreak())

# ---------- PAGE 5 : TEMPLATE WORKSHEET ----------
E.append(Paragraph("WRITE YOUR OWN PROMPT", st_h1))
E.append(Paragraph("Session 2 homework · Fill in the blanks — this becomes your agent's job description", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(Paragraph("You are ⟨name your agent⟩, the assistant for ⟨business/person⟩.<br/>Goal: ⟨trigger⟩ + ⟨action⟩ + ⟨done-condition⟩.<br/>Tone: ⟨3 adjectives⟩. Language: ⟨which⟩.<br/>Tools allowed: ⟨1⟩, ⟨2⟩, ⟨3⟩ (max).<br/>NEVER: 1) ⟨hardest rule⟩  2) ⟨second rule⟩  3) ⟨third rule⟩.<br/>If asked for something on the NEVER list → use ask_human().<br/>Log every action with log_sheet().", st_code))
E.append(lines(1))
E.append(Paragraph("Loop pseudocode — copy the pattern", st_h2g))
E.append(Paragraph("while not goal_done and steps &lt; 10:<br/>&nbsp;&nbsp;&nbsp;&nbsp;step   = brain.think(goal, history)<br/>&nbsp;&nbsp;&nbsp;&nbsp;result = act(step.tool, step.inputs)<br/>&nbsp;&nbsp;&nbsp;&nbsp;history.append(observe(result))<br/>&nbsp;&nbsp;&nbsp;&nbsp;if result looks wrong:<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;history.append(ask_human(result))", st_code))
E.append(Paragraph("Adapt it to YOUR agent below:", st_body))
E.append(write_zone(6, ""))
E.append(PageBreak())

# ---------- PAGE 6 : SESSION 1 HOMEWORK ----------
E.append(Paragraph("HOMEWORK — SESSION 1", st_h1))
E.append(Paragraph("Your 3 wish-tasks · Due: before Session 2", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(Paragraph("Rules: make each task concrete — WHO it is for, WHAT it does, WHEN it happens, HOW OFTEN. If you cannot say when it is done, it is not a task yet.", st_body))
for i in (1, 2, 3):
    E.append(Paragraph(f"Wish-task #{i}", st_h2))
    E.append(box_table([["Who is it for?", ""], ["What should the agent do?", ""], ["When / how often?", ""], ["What does 'done' look like?", ""], ["Tools it would need", ""], ["What must it NEVER do?", ""]], [5.6 * cm, PW - 2 * M - 5.6 * cm]))
    E.append(Spacer(1, 0.25 * cm))
E.append(PageBreak())

# ---------- PAGE 7 : SESSION 2 HOMEWORK ----------
E.append(Paragraph("HOMEWORK — SESSION 2", st_h1))
E.append(Paragraph("Design wish-task #1 · Due: before Session 3", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table([["GOAL (trigger + action + done)", ""], ["TRIGGER — what wakes the agent?", ""], ["TOOLS (name, inputs, output)", ""], ["STOP CONDITION (max steps / time)", ""], ["ESCALATE when… (ask_human)", ""]], [7.2 * cm, PW - 2 * M - 7.2 * cm]))
E.append(lines(1))
E.append(Paragraph("My agent's instruction prompt (8–12 lines)", st_h2g))
E.append(write_zone(9, ""))
E.append(Paragraph("Check yourself: does the prompt say WHO, WHAT GOAL, TONE, and at least one hard NEVER? If not, add it.", st_note))
E.append(PageBreak())

# ---------- PAGE 8 : SESSION 3 HOMEWORK ----------
E.append(Paragraph("HOMEWORK — SESSION 3", st_h1))
E.append(Paragraph("Put it on WhatsApp · Due: before Session 4", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table([["Agent's NAME", ""], ["First message it sends (identity intro, 2 lines)", ""], ["Guardrails: NEVERs, caps, human gates", ""], ["Rate limits (msgs/min, night mode?)", ""], ["What needs MY approval before it acts?", ""]], [7.2 * cm, PW - 2 * M - 7.2 * cm]))
E.append(lines(1))
E.append(Paragraph("Sketch the round trip for YOUR task", st_h2g))
E.append(Paragraph("Customer message → WhatsApp Web → MCP bridge → agent loop → reply → log. Draw arrows and label what happens at each step for your task:", st_body))
E.append(write_zone(7, ""))
E.append(PageBreak())

# ---------- PAGE 9 : SESSION 4 HOMEWORK ----------
E.append(Paragraph("HOMEWORK — SESSION 4", st_h1))
E.append(Paragraph("Ship it & earn · Due: Day 30", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(Paragraph("Shipping checklist — tick every box:", st_body))
E.append(box_table([["Restart-proof", "Agent restarts itself after a crash"], ["Logs", "Writes logs I actually read weekly"], ["Guardrails ON", "Step caps + human gates still active"], ["One-command pause", "I can stop it instantly"], ["Friend-tested", "Someone else tried it and it held"], ["Certificate submission", "Goal + tools list + prompt + 1 screenshot"]], [5.2 * cm, PW - 2 * M - 5.2 * cm]))
E.append(lines(1))
E.append(Paragraph("First client plan", st_h2o))
E.append(box_table([["Client 1 (who?)", ""], ["Their repetitive task", ""], ["Hours it eats monthly", ""], ["My setup fee / monthly care price", ""], ["Demo date I will offer", ""]], [6.4 * cm, PW - 2 * M - 6.4 * cm]))
E.append(PageBreak())

# ---------- PAGE 10 : FIRST AGENT WORKSHEET ----------
E.append(Paragraph("MY FIRST AGENT — MASTER WORKSHEET", st_h1))
E.append(Paragraph("One page to run your agent. Photocopy this for agent #2 and #3.", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table([["1. NAME", ""], ["2. GOAL", ""], ["3. TRIGGER", ""], ["4. TOOLS (max 4)", ""], ["5. PROMPT (paste final version)", ""], ["6. GUARDRAILS", ""], ["7. STOP CONDITION", ""], ["8. LOG LOCATION", ""], ["9. FIRST TEST DATE", ""], ["10. FIRST USER", ""]], [6.2 * cm, PW - 2 * M - 6.2 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph("The 30-day map", st_h2o))
E.append(box_table([["Week 1 (S1)", "☐ anatomy learned   ☐ 3 wish-tasks written"], ["Week 2 (S2)", "☐ goal written   ☐ tools listed   ☐ prompt drafted"], ["Week 3 (S3)", "☐ trigger set   ☐ guardrails set   ☐ round trip sketched"], ["Week 4 (S4)", "☐ shipped   ☐ first user   ☐ first invoice / first ask"]], [3.4 * cm, PW - 2 * M - 3.4 * cm]))
E.append(PageBreak())

# ---------- PAGE 11 : NOTES + SAFETY CARD ----------
E.append(Paragraph("SAFETY CARD — pin this above your desk", st_h1))
E.append(Paragraph("From Session 3 · The three walls", st_kick))
E.append(Spacer(1, 0.2 * cm))
E.append(box_table([["IDENTITY", "It says it is an assistant — never a human. One name, everywhere, no borrowed photos, no fake feelings."],
                   ["PACING", "One reply per customer message. Night mode. Hard rate limit. No broadcasts to strangers, ever."],
                   ["HUMAN APPROVAL", "Payments, discounts, dates, promises, refunds → ask_human() first. No answer in 15 min → wait, do not guess."]],
                  [4.2 * cm, PW - 2 * M - 4.2 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph("Failure map — where it will break first", st_h2))
E.append(box_table([["Loops forever", "Add step cap + stop condition"], ["Robotic replies", "Rewrite prompt; add one worked example"], ["Misses messages", "Check WhatsApp Web login / bridge"], ["Invents facts", "Give it a tool that reads real data"], ["Tool-call storms", "One job per tool; stricter NEVER list"]], [5.6 * cm, PW - 2 * M - 5.6 * cm]))
E.append(lines(1))
E.append(Paragraph("Notes from class", st_h2g))
E.append(write_zone(6, ""))
E.append(PageBreak())

# ---------- PAGE 12 : CLOSING ----------
E.append(Spacer(1, 3.2 * cm))
E.append(Paragraph("GOAL → THINK → ACT → OBSERVE → REPEAT", ParagraphStyle("mantra", fontName="Helvetica-Bold", fontSize=20, leading=26, textColor=DARK_BLUE, alignment=TA_CENTER)))
E.append(Spacer(1, 0.5 * cm))
E.append(Paragraph("You started with a wish-list.<br/>You leave with an agent.", ParagraphStyle("close", fontName="Helvetica", fontSize=14, leading=20, textColor=GREY, alignment=TA_CENTER)))
E.append(Spacer(1, 1.2 * cm))
E.append(Paragraph("Stay hungry. Stay foolish.", ParagraphStyle("sf", fontName="Helvetica-BoldOblique", fontSize=16, leading=22, textColor=GREEN, alignment=TA_CENTER)))
E.append(Spacer(1, 1.5 * cm))
E.append(Paragraph("AGENT SCHOOL — COHORT 1", ParagraphStyle("ft", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=ORANGE, alignment=TA_CENTER)))

doc.build(E)
print("SAVED", OUT)

