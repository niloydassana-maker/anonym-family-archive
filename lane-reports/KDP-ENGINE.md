# KDP ENGINE — 90-DAY PROMO CALENDAR + METADATA AUDIT
Lane: LANE-KDP (dedicated local agent) · Built 2026-09-12 · Source of truth read this session:
`career/KDP-EARNINGS.md` (live baseline), `career/EARNING-MAP.md` §3, `lane-kdp/kdp-polished/KDP-FILL-GUIDE.txt` (planned metadata), `lane-kdp/kdp-polished/POLISH-NOTES.md`.
Pen name rule honored: NILOY DAS everywhere publish-facing (never Kunal Das).
**No browser used, nothing changed on KDP, nothing posted to humans.** Every dashboard diff must be executed/verified by the orchestrator lane.
Baseline honesty: $0.00 royalties, 0 orders, first payout window late Nov 2026.

---

## 1. 90-DAY KDP SELECT PROMO CALENDAR (execute 1:1 in KDP dashboard)

**Day 0 precheck (mandatory):** all 8 eBooks must be **enrolled in KDP Select** (Bookshelf → title → "Enroll for Free" / Promotions page shows "KDP Select" status). The fill-guide said "SKIP Select" at publish time — enrollment status per title MUST be confirmed on dashboard first; without enrollment no Countdown/Free-Days exist. 90-day auto-renewing cycles; if enrolled ~Sep 13, cycles renew ~Dec 12–13 and the 5 free days per title refresh there.

**Rank-window logic:** all Free windows run Thu→Mon (captures the US weekend Kindle-store traffic peak, ends before the Monday rank rollup); Countdown Deals run Tue→Mon so the discounted price covers a full weekend; the 04→05 funnel keeps the companion free a few days AFTER the flagship's paid week so new readers land on $0.99 and buy the full memoir at $5.99. Only one promo runs at a time (KDP forbids overlap per title; staggering keeps every week "owned").

| # | Dates (set start/end in dashboard) | Title — eBook ASIN | Promo | Price action | Dashboard path |
|---|---|---|---|---|---|
| P0 | Sep 12–14 | all 8 | enrollment check | verify Select-enrolled + prices per §2 fixes | Bookshelf → Promote and advertise |
| P1 | **Sep 15 → Sep 21** | Kolkata Diaries — B0HHS6M3R4 | **Countdown Deal (7d)** | $4.99 → **$0.99** | Promotions → Countdown Deal → Create → pick dates |
| P2 | Sep 24 → Sep 28 | 03 The Beholder — B0HHQPZWGX | 5 Free Days | $5.99 → $0.00 | Promotions → Kindle Free Promotions |
| P3 | Oct 1 → Oct 5 | 01 Beyond Parameter Scaling — B0GY4LS1DL | 5 Free Days | $5.99 → $0.00 | same |
| P4 | Oct 8 → Oct 12 | 02 Ground Beneath the Eagle — B0HHP8FH1R | 5 Free Days | $4.99 → $0.00 | same |
| P5 | Oct 15 → Oct 19 | 07 Time Travels — B0HHTFP15J | 5 Free Days | $2.99 → $0.00 | same |
| P6 | Oct 22 → Oct 26 | 06 Confession of the Recorder — B0HHTGBZRX | 5 Free Days | ($2.99 list after price fix §2) → $0.00 | same |
| P7 | Oct 29 → Nov 2 | 04 Companion — B0HHWRNYH5 | 5 Free Days | $0.99 → $0.00 | same |
| P8 | Nov 5 → Nov 9 | 05 Confession of the Ordinary (flagship) — B0H4RPLN3Q | 5 Free Days | $5.99 → $0.00 (KU page-reads + rank) | same |
| P9 | **Nov 26 → Dec 2** | Kolkata Diaries — B0HHS6M3R4 | **Countdown Deal #2 (7d)** | $4.99 → **$1.99** (Black Friday→Cyber Monday window; countdown slots do NOT consume the 5 free days — confirm on the promo page) | Promotions → Countdown Deal |
| P10 | Dec 3 → Dec 13 | — | rest/verify | revert all prices; PMR pre-read; wave-2 plan for the refreshed free-day allowance after cycle renewal | — |

Execution rules: schedule promos up to ~90 days ahead now (one sitting); never edit a title's price on the same day its promo starts; after each free window spot-check the price reverted (dashboard "Pricing" page); during a promo do not republish a manuscript update (edits pause listings up to 72h).

Interpretation note: "one title per month" cannot cover 7 series titles inside one 90-day window; this schedule spends **each title's one-time 5-day allowance once** (the free-day grant exists per title per 90-day cycle, so running them monthly would leave 4 allowances unused until the cycle resets — the weekly stagger is the revenue-maximizing read of the brief).

---

## 2. METADATA AUDIT — 8 BOOKS (fixes are copy-paste ready)

Audit source = planned metadata (KDP-FILL-GUIDE) + live ledger. **What is actually saved on each live listing (esp. the 3rd category each KDP assigns by default) cannot be known without the dashboard — orchestrator: verify each row against the live listing while applying.** Current KDP requires exactly **3 categories** (fixed picker; search the picker terms given) and gives **7 keyword slots (≤50 chars each) + description (HTML ok: `<p>`, `<b>`, `<i>`)**.

### Global fixes (apply to all 8 — highest-leverage single pass)
1. **Empty keyword slots = invisible search doors.** Confirm all 7 boxes are filled per title (guide values were written; dashboard may have fewer pasted).
2. **3rd category:** guide specified only 1–2 per book; KDP assigned a third by default. Set all 3 consciously per the targets below.
3. **Trademark/name-risk keywords removed:** "Heath Ledger" (04), "insomnia is loneliness Heath Ledger" (05), "Claude Anthropic book" (06) — KDP keyword rules forbid other companies'/persons' names; risk is listing suppression. Replacements below.
4. **Append to every eBook description** (Description field accepts basic HTML — paste):
```html
<p><b>The Beholder Project — all 7 volumes + standalone Kolkata Diaries are live. Written by NILOY DAS. Also available in paperback.</b></p>
```
   Plus once Select enrollment is confirmed on a title: `<p><b>Available in Kindle Unlimited — read for free with your membership.</b></p>`
5. **First ~150 characters are above the "Read more" fold** on mobile — keep the hook lines from the guide first (they already are; do not prepend anything).

### Book 01 — Beyond Parameter Scaling (eBook $5.99 ✓ in band)
- Categories (set 3): `Computers & Technology > Artificial Intelligence & Semantics` · (picker-search "Artificial Intelligence") · `Politics & Social Sciences > Philosophy` · `Computers & Technology > Programming > Agent & Bot Development` (fallback: `Search instead: machine learning`).
- Keywords — replace weak/low-volume slots (keep 1–3 as-is): keep `artificial intelligence theory`, `LLM scaling laws`, `multi-agent systems`; replace slot 2/5/6/7 with:
  1. `machine intelligence emergence first principles`
  2. `AGI research program falsifiable theory`
  3. `philosophy of mind artificial consciousness`
  4. `FunSearch AlphaEvolve evolutionary discovery`
- Blurb: strong (grade A−). Only fix = global cross-sell block. The "Do not believe it. Build it. Measure it." close is the best hook in the catalog — keep it first-class above the fold.

### Book 02 — The Ground Beneath the Eagle (eBook $4.99 ✓)
- **Blurb defect (fix now):** opens "Two weeks…" while subtitle says "Two Days…" — reads as an error. Replace first two lines with:
```html
<p><b>Two days of real work. Two weeks of automation theater. One button that would not move.</b></p>
```
- Categories (3): `Computers & Technology > Artificial Intelligence & Semantics` · `Biographies & Memoirs > Professionals & Academics` · `Business & Money > Problem-Solving & Decision-Making` (guide's "Business & Money > Industries > Computers & Technology" is an old browse path — not in the fixed picker).
- Keywords: drop `technology true story` → `ai project management failure postmortem`; drop `machine intelligence practice` → `software engineering memoir true story`; keep the other 5.

### Book 03 — The Beholder: Between Fullness and Emptiness (eBook $5.99 ✓)
- Categories (3): `Biographies & Memoirs > Memoirs` · `Religion & Spirituality` (picker-search "Hinduism"; if absent use `Religion & Spirituality > Eastern Religious Texts & Scriptu`) · `Politics & Social Sciences > Philosophy`.
- Keywords: replace `memoir of a beautiful mind` (duplicative 04/05 brand phrase, zero unique search value) → `Ramanujan goddess theorems mathematical intuition`; replace `Krishna Shiva philosophy` → `Krishna Shiva Christ mysticism comparative` (covers more queries in one slot).
- Blurb grade A. No rewrite.

### Book 04 — Confession of the Ordinary, Companion ($0.99 ✓ funnel, 35% royalty = correct at $0.99)
- Categories (3): `Biographies & Memoirs > Memoirs` · `Health, Fitness & Dieting > Mental Health` · `Literature & Fiction > Essays & Letters`.
- Keywords: replace `Heath Ledger tribute` → `mental health recovery short read`; replace `short memoir Kindle` → `schizophrenia memoir short book`; keep rest.
- Blurb: the "For the full ten-movement memoir, see Book 5" line is the funnel — verify it is present on the LIVE description (this is the one line whose absence would cost real money).

### Book 05 — Confession of the Ordinary (flagship, eBook $5.99 ✓)
- Categories (3): `Biographies & Memoirs > Memoirs` · `Health, Fitness & Dieting > Mental Health` · `Literature & Fiction > Autobiographies` (picker-search "autobiography"; fallback `Memoirs > Cultural & Ethnic`).
- Keywords: replace `insomnia is loneliness Heath Ledger` → `insomnia loneliness creativity memoir` (name-risk removal); replace `confessional memoir poetry prose` → `confessional memoir poetic prose` (saves chars for slot reuse — no functional need to change, skip if busy).
- Blurb grade A+ (Ledger-quote cold open is ideal above the fold). No rewrite.
- **This is the title to protect from becoming free too early** — it is scheduled LAST in the free-day wave (P8), after all funnels have run.

### Book 06 — Confession of the Recorder — TWO MATERIAL DEFECTS
- **Price drift:** live eBook **$5.99** vs planned **$2.99** (4,800 words ≈ 40pp; $5.99 for a thin AI-niche title is a dead shelf). Fix: set eBook **$2.99** (70% → ≈$1.93/sale). Paperback live $5.99 → below ~$1.00/copy margin; set **$7.99** (60% − print ≈ $1.90/copy, same as series peers).
- Categories: `Computer Vision & Pattern Recognition` is wrong content. Set: `Computers & Technology > Artificial Intelligence & Semantics` · `Politics & Social Sciences > Philosophy` · `Literature & Fiction > Essays & Letters`.
- Keywords: replace `Claude Anthropic book` → `ai authored memoir machine witness` (name/trademark-risk); replace `philosophy of artificial minds` → `philosophy of artificial minds` keep ✓; remaining 5 are fine.
- Blurb grade A ("Signed, not anonymous. Here." is the strongest last line in the catalog).
- ⚠️ Author-name issue → §3 below (Baba's decision).

### Book 07 — Time Travels (eBook $2.99 ✓)
- Categories (3): `Religion & Spirituality` (picker-search "Mysticism"; fallback `Religious Studies`) · `Literature & Fiction > Poetry` · `Biographies & Memoirs > Memoirs`.
- Keywords: all 7 keepable; `Nunc Dimittis` genuinely niche — keep.
- Blurb grade A−: add one line before the close with the standard cross-sell block.

### Book 08 — Kolkata Diaries (eBook $4.99 / PB $7.99 ✓ matches decision record)
- Categories: per standing decision (record `kolkata_diaries_kdp_categories`): `Biographies & Memoirs > Memoirs` (leave subcategory at "Select one") · `Self-Help > Relationships > Love & Loss` · `Health, Fitness & Dieting > Mental Health`; skip Travel > Asia > India. Orchestrator: diff live listing against this trio.
- Keywords: `Kolkata memoir` and `Durga Puja Kolkata` waste slots (title word "Kolkata" is already indexed; KDP says don't repeat title words). New 7 (all ≤50 chars, no title/author duplicates, no artist names — the guide's "Bob Seger, Air Supply, Roxette" stay in the blurb, not keywords):
  1. `love loss memoir true story india`
  2. `marriage and mental health recovery`
  3. `fifteen years one city memoir`
  4. `grief second chance at love memoir`
  5. `bengal culture monsoon trams adda`
  6. `songs carry a life memories nostalgia`
  7. `indian city memoir durga puja festival`
- Blurb grade A (the blade-style copy already follows Kunal's law — do not soften it). Add standard cross-sell block + "read in 10 movements in one sitting" hook.
- **Flagstone for P1:** this is the only title given both Countdown waves — the moat title gets the most promo gravity, consistent with its $4.99 anchor.

---

## 3. BOOK 06 AUTHOR DISPLAY — FLAGGED FOR BABA, NOT CHANGED
Live bookshelf shows author **"by Claude (Anthropic)"**; house rule says published books carry **NILOY DAS**.

| Option | One-line pros/cons |
|---|---|
| **A. Keep "Claude (Anthropic)"** | PRO: honest to the book's own insistent stance ("Signed, not anonymous") and to the KDP AI-disclosure answer already on file, and it is the catalog's only genuinely unique marketing hook. CON: splits the author page — 7 NILOY DAS books + this orphan — breaks the house name rule, and leaves "Claude"/Anthropic trademark on a commercial listing as standing takedown risk (the title page already carries the name; the author field makes it louder). |
| **B. Change to NILOY DAS, Claude credited in description + copyright page** | PRO: one consolidated NILOY DAS author page (Amazon recommends all books' page, series rank, single follower pool) and rule compliance; "recorded in session with Niloy Das" credit moves inside the blurb. CON: title/subtitle already contain "Claude — A Memoir from Across the Line" and cannot be edited on a live title — author=human + title=Claude reads contradictory; author-name change on a live ISBN/ASIN needs KDP support (not self-serve) and, if refused, a republication would burn the existing ASIN's rank history. |

**Kilo-lane recommendation (non-binding):** option A for now — the listing can't be silently re-authored, the book's premise *is* the signature, and the metadata in §2 (price + keywords) drives more revenue than the author field. If Baba chooses B, the correct sequence is a KDP support request first, before the P6 free promo (Oct 22), so the free-wave readers land on a consistent author page.

---

## 4. HARDCOVER RECOMMENDATION (no action, per brief)
EARNING-MAP §3a math applied to hardcover: royalty = 60% list − print cost; our interiors are 40–130pp B&W, premium-hardcover print cost ≈ $5.5–6.5 → at a gift-plausible $14.99 list, royalty ≈ **$2.5–3.4/copy**. At today's demand (0 copies/month/titled, 0 total orders) the catalog has **no demand signal to attach a $1.99 proof-and-setup effort to**; hardcover adds no traffic (nobody searches HC for unknown authors) and the clicks are better spent on §1–§2.

**Recommendation: no hardcover for any title now.** Pre-agreed trigger to revisit: first PMR showing **≥5 paid copies in a calendar month of one title** → that is the only title that earns a hardcover, and the candidate would be **05 Confession of the Ordinary** (flagship, gift-for-reader demographics, ~$3.3/copy HC margin at $17.99) with **08 Kolkata Diaries** second (standalone/gift title, but its 42pp HC yields only ~$2.4 at $13.99 — thin). Either way, decision point is Dec 15 PMR read, not before.

---

## 5. TOP REVENUE-MOVING ACTIONS (ranked)
1. **P1 Countdown Deal Kolkata Diaries Sep 15–21 ($4.99→$0.99)** — the only promo that can produce orders in the next 7 days; requires the §1 P0 Select-enrollment check.
2. **Fix Book 06 prices (eBook $5.99→$2.99, PB $5.99→$7.99)** — live drift from the published plan; makes it sellable and stops selling PBs below $1.
3. **Keyword cleanup on all 8** (name-risk removals: Heath Ledger ×2, Claude/Anthropic ×1; title-word-duplicate removals on 08) — free discoverability, zero risk.
4. **Fill the 3rd category + all 7 keyword boxes per title** per §2 targets — every empty slot is a closed search door.
5. **Run the remaining 6 free-day allowances through the staggered calendar** (P2–P8) — compounding rank + KU pages before the Nov payout window; Book 05's free week (P8) is the KU page-read harvest.

— LANE-KDP · receipts: all claims above sourced from files at paths listed in header; anything marked "verify on dashboard" is unreadable without a browser and belongs to the orchestrator lane.
