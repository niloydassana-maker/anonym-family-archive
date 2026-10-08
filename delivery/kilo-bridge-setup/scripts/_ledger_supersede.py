"""_ledger_supersede.py - append honest SUPERSEDE rows to the employment ledger.
MISLABEL CLAUSE (AGENTS.md 34.4.2): a report may never stamp a claim the artifact
does not show. Two rows logged the list-page widget as the blocker; one row stamped
APPLIED though the recruiter gate was never answered. Append-only TSV corrections.
"""
import io
from datetime import date
from pathlib import Path

LEDGER = Path(r"D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\ledger.tsv")
JOBS = "https://www.naukri.com/mnjuser/recommendedjobs"
ROLE = "GenAI Architect | Generative AI | LLM | RAG | Agentic AI"
today = str(date.today())

rows = [
    [today, "naukri", JOBS, ROLE, "-", "-",
     "SUPERSEDE: widget logged as recruiter question", "CORRECTED",
     "scripts/lane_apply.py",
     "The 00:11 and 00:36 BLOCKED rows logged 'Are these jobs relevant for you?' "
     "- that is the SPAN.feed-title list alignment widget, NOT the apply gate. "
     "Real question = 'How many years of hands-on experience do you have in GenAI/LLM?' "
     "(_find_question now reads ONLY DIV.chatbot_MessageContainer)."],
    [today, "naukri", JOBS, ROLE, "-", "-",
     "SUPERSEDE: 'apply flow opened' mislabeled as APPLIED", "CORRECTED",
     "scripts/lane_apply.py",
     "Row 00:42 (apply-03-after-apply-20261007004258) declared APPLIED although the "
     "recruiter gate was NOT answered (panel showed 'How many years ...?'). The flow "
     "OPENED (true) but nothing was submitted. Verdict = BLOCKED (gate open, question "
     "unanswerable: no apply_answers.txt). No honest APPLIED row exists yet."],
]

text = "\n".join("\t".join(r) for r in rows) + "\n"
with io.open(LEDGER, "a", encoding="utf-8") as fh:
    fh.write(text)
print("SUPERSEDE rows appended:", len(rows))