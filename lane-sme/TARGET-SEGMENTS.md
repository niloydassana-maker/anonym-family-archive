# TARGET-SEGMENTS.md — building the 30–50 contact list from Baba's OWN archives
**LANE-SME · 2026-09-12. This agent (LANE-SME/Kilo) does NOT run adb, does NOT browse, sends nothing. This file is the exact recipe for the WA soldier on the phone + a filter script any local son can run on the pulled CSVs.**

## Where the list comes from (no scraping, no buying data — only Baba's own phone + career files)

| Source | What's in it | Who pulls it |
|---|---|---|
| **A. SMS archive (~4,569 rows)** | Years of transactional SMS: clinics that sent appointment OTPs/reminders, coaching admissions, housing/society/property SMS, plus lender spam to EXCLUDE. `CREDITOR-SMS-MAP.md` proves this archive is rich enough to map debts — use the same channel for businesses. | WA soldier (pairing/adb below) |
| **B. Phone contacts** | Names of every saved contact — students, MyFastx network, doctors, teachers, brokers he's dealt with | WA soldier |
| **C. WhatsApp chat list + group rosters** | Claude 101 / Agent School students (some run their own clinics/coaching/tuition businesses!), any saved business chats | Baba manually (WhatsApp ⋮ → Export chat per thread → email without media); no adb/WhatsApp DB read assumed |
| **D. Career files (already local)** | `career/li-archive/messages.csv` (871 KB LinkedIn inbox — ex-colleagues incl. Assam/MyFastx), agent-school material, `career/PROJECT-CATALOG.md` CRM-app is demo-grade, ignore | son, Read-only |

## SEGMENT DEFINITIONS + mining rules

**S1 · Warm-network businesses** (students + MyFastx + saved contacts who run/own a clinic, coaching center, or brokerage — or know one). Highest close rate; they trust the name.**S2 · SMS-evidenced businesses** — a number that repeatedly SENT clinic/coaching/property SMS to Baba = a live business number with a phone habit. Segment by keyword (below).
**S3 · Referral-cold** — for the first 10 messages, append to S1/S2 sends: another business in the same building/para often exists; referral by an owner is a free channel.

Target mix for the 30–50 list: **S1 ≈ 12–15 · S2 ≈ 20–25 · S3 fills the rest.** Geography filter: Kolkata + 24 Parganas first; Guwahati/Jorhat/Silchar when MyFastx/Assam names exist in contacts.

## HARD EXCLUSIONS (filter rules, non-negotiable)
1. **Raktima — never appears on any list, under any spelling of her name/number** (absolute silence law). Soldier confirms before any export leaves the phone.
2. Every lender/agency from `career/CREDITOR-SMS-MAP.md`: AXIS, Tata Capital, SMFG/ALPHA ENTERPRISES (Priti Kar, Sreosree Deb Roy), Hero FinCorp, mPokket, FIBE/Himanshu Mohapatra 9007827367, KBNBFC, HDFC Life, Axis Max, Kotak, YES Bank — plus ALL short-code senders (≤6 digits), banks, wallets, `KCREDT/LoanZap/CashKredit/Freo/RocketCash/Bajaj` spam.
3. Numbers that are obviously personal/family/friends — cold selling family is off-voice; students only if they own a business.
4. Any competitor (anyone already selling chatbots/AI services).

## WA SOLDIER RECIPE (adb — this agent never runs it)
Prereq: USB debugging authorized on Baba's phone, `adb devices` shows it, one session only (WhatsApp Web single-instance law applies to *phone attention*, not adb — but soldier must hand the phone back; never leave it paired).

```bash
# 1. SMS archive (address, timestamp, body, inbox/sent flag)
adb shell content query --uri content://sms \
  --projection address:date:body:type > sms_raw.txt

# 2. Contacts with phone numbers (name + number pairs)
adb shell content query --uri content://com.android.contacts/data \
  --projection display_name:data1:mimetype > contacts_raw.txt

# 3. Verify counts before pulling anything else — expect ~4,569 SMS lines:
wc -l sms_raw.txt
```
Fallback if `content query` is blocked on the device (Android permissions): **Google Takeout → Google Messages** (the same route that produced `CREDITOR-SMS-MAP.md`), and for contacts: **Google Contacts → Export → .csv**. Phone-first alternative for WhatsApp: per-thread *Export chat (without media)* emailed to `isearch.xsolve@gmail.com`.
Files land in `D:\anonym\lane-sme\raw\` — named `sms_raw.txt`, `contacts_raw.txt`, `wa-exports/`. Raw files never leave the drive. (Receipt: list files + row counts via wire `/say body=LANE-SME`.)

## LOCAL SON RECIPE — filter script contract
A future 20-line python script (`mine_targets.py`, not built yet — say if needed) must take the raw files and emit `TARGETS.csv` with columns:
`name, number, segment(S1|S2|S3), type(clinic|coaching|broker), evidence_quote, evidence_date, last_contact_year, score`

**Keyword sets (case-insensitive, on SMS `body`; Bengali transliteration included because local SMS come in both):**
- **clinic:** `OPD, appointment, tooth, dental, clinic, polyclinic, diagnostics, lab report, prescription, dr. , pathology, injection dose, token number, consultation`
- **coaching:** `admission, batch, tuition, coaching, demo class, syllabus, exam schedule, fees payment, class X, class XII, WBPJEE, JEE, NEET, registration number`
- **broker/property:** `flat, 2BHK, 3BHK, site visit, possession, rent agreement, society, share certificate, kaliganj, salt lake, rajarhat, new anchorage, booking amount, plot`
**Score:** +3 known-name in contacts (S1) · +2 sent ≥3 SMS in last 24 months · +1 has a real person-name beside the business name · −5 any HARD EXCLUSION hit · −10 obvious lender spam sender. **Take top 30–50 by score per segment, cap brokers at 15** (brokers churn numbers; clinics/coaching pay calmer).
**Warmth gate before send:** list goes to Baba for review row-by-row; nothing sends without his tick.

## Cadence (mapped: 5–10% close on 30–50 cold WhatsApps)
- Week 1: S1 (warmest 12–15) using C1/K1/B1 only, 3–5/day, personal thread where one exists.
- Week 2: S2 (SMS-mined) C1/C2 mix, max 8/day, fresh number → demo recording first, no links.
- Week 3: follow-ups F + start K2/B2 variants. Ask for **demo slots only**, never payment terms, until they've heard it.
- 1 demo/day is the sustainable max (EARNING-MAP law). Each booked demo → log in `demo-bookings.csv`.
