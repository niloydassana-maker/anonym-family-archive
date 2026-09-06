#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render PARTHA-DEB-RESUME-FINAL.md as a clean single-page ATS-friendly PDF.

Built by Kilo (Brother-4) for Partha Deb's job-hunt kit, 2026-09-06.
[ASK DA] placeholders render as bracketed fields to be filled.
"""
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
)

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "PARTHA-DEB-RESUME-FINAL.md")
OUT = os.path.join(BASE, "Partha_Deb_Resume.pdf")

INK = HexColor("#1a1a1a")
GREY = HexColor("#444444")
LINE = HexColor("#888888")
ACCENT = HexColor("#2c3e50")

name_st = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=20,
                         leading=24, alignment=TA_CENTER, textColor=INK)
tag_st = ParagraphStyle("tag", fontName="Helvetica", fontSize=10.5,
                        leading=14, alignment=TA_CENTER, textColor=ACCENT)
contact_st = ParagraphStyle("contact", fontName="Helvetica", fontSize=9.5,
                            leading=13, alignment=TA_CENTER, textColor=GREY)
h2_st = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5,
                       leading=15, textColor=ACCENT, spaceBefore=8, spaceAfter=2)
body_st = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                         leading=13, textColor=INK)
job_st = ParagraphStyle("job", fontName="Helvetica-Bold", fontSize=10.5,
                        leading=14, textColor=INK, spaceBefore=6)
dates_st = ParagraphStyle("dates", fontName="Helvetica-BoldOblique", fontSize=9.5,
                          leading=13, textColor=GREY)
bullet_st = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                           leading=12.5, textColor=INK, leftIndent=14)
ask_st = ParagraphStyle("ask", fontName="Helvetica-Oblique", fontSize=9.5,
                        leading=13, textColor=GREY, leftIndent=14)


def para(text, style):
    text = text.replace("[ASK DA", "<b>[ASK DA</b>")
    return Paragraph(text, style)


def build():
    with open(SRC, encoding="utf-8") as f:
        lines = f.read().splitlines()

    # Skip the internal header block (everything before the exact '# PARTHA DEB' H1)
    start = next(i for i, l in enumerate(lines) if l.strip() == "# PARTHA DEB")
    lines = lines[start:]

    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=12 * mm, bottomMargin=10 * mm,
        title="Partha Deb - Resume",
        author="Partha Deb",
    )

    story, bullets, in_bullets = [], [], False

    def flush_bullets():
        nonlocal bullets, in_bullets
        if bullets:
            story.append(ListFlowable(
                [ListItem(para(b, ask_st if b.startswith("[ASK DA") else bullet_st))
                 for b in bullets],
                bulletType="bullet", start="•", leftIndent=14))
            bullets, in_bullets = [], False

    for raw in lines:
        line = raw.rstrip()
        if not line or line == "---":
            continue
        if line.startswith("# "):
            flush_bullets()
            story.append(para(line[2:], name_st))
            story.append(Spacer(1, 2))
        elif line.startswith("## "):
            flush_bullets()
            story.append(para(line[3:], h2_st))
            story.append(HRFlowable(width="100%", thickness=0.7, color=LINE,
                                    spaceBefore=1, spaceAfter=4))
        elif line.startswith("### "):
            flush_bullets()
            story.append(para(line[4:], job_st))
        elif line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            flush_bullets()
            story.append(para(line.strip("*"), dates_st))
        elif line.startswith("- "):
            bullets.append(line[2:])
            in_bullets = True
        elif in_bullets:
            # continuation line of a bullet block (e.g. Career Break text)
            bullets.append(line)
        elif line.startswith("*") or line.startswith("Baduria") or \
                line.startswith("Phone:") or line.startswith("LinkedIn:"):
            flush_bullets()
            if line.startswith("Baduria"):
                story.append(Spacer(1, 2))
                story.append(para(line, contact_st))
            elif line.startswith("Phone:"):
                story.append(para(line, contact_st))
            elif line.startswith("LinkedIn:"):
                story.append(para(line, contact_st))
                story.append(Spacer(1, 4))
        else:
            flush_bullets()
            if line.startswith("**IT Support"):
                story.append(para(line.strip("*"), tag_st))
            elif line.startswith("[ASK DA"):
                story.append(para(line, ask_st))
            else:
                story.append(para(line, body_st))
    flush_bullets()

    doc.build(story)
    size = os.path.getsize(OUT)
    print("PDF written: %s (%d bytes)" % (OUT, size))
    return size


if __name__ == "__main__":
    build()
