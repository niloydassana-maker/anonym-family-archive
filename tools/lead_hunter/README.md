# Public buyer lead hunter

Standard-library Python 3.10+ script. Extracts emails, explicit international phone
numbers, tel links, WhatsApp links and LinkedIn `/in/` profiles from public buyer
briefs. Does not log in, send messages, guess addresses or verify deliverability.

## Run from PowerShell

```powershell
python D:\anonym\tools\lead_hunter\hunt_leads.py --discover --max-pages 10 --out D:\anonym\tools\lead_hunter\output --suppress-file D:\anonym\tools\lead_hunter\already_contacted.json
```

For a specific brief or several saved source URLs:

```powershell
python D:\anonym\tools\lead_hunter\hunt_leads.py --url 'https://community.n8n.io/t/323364' --days 30
python D:\anonym\tools\lead_hunter\hunt_leads.py --urls-file buyer_urls.txt
```

`buyer_urls.txt` contains one URL per line. `#` comments are allowed. Default
discovery scans the latest public n8n Jobs category page, not the entire internet.
Make forum threads can be supplied using `--url` or discovered via search.

## Optional broad search

Set `BRAVE_SEARCH_API_KEY` in your environment using your own API account, then:

```powershell
python D:\anonym\tools\lead_hunter\hunt_leads.py --search --discover --max-pages 20
python D:\anonym\tools\lead_hunter\hunt_leads.py --search --query '"hiring" "n8n" "paid" "Singapore"'
```

This uses an external search API and may incur provider charges. No key is needed
for direct URLs or n8n discovery. Do not paste secrets into code or commit them.
API reference: https://api-dashboard.search.brave.com/api-reference/web/search/post

## Outputs and evidence

All four coordinates are first-class fields in `leads.json` and `leads.csv`:
`linkedin`, `phone`, `whatsapp_number`, and `email`. Each has a separate status:
`published_candidate` or `not_found_in_scanned_content`. `coordinate_count` is
0–4. JSON retains evidence and source URLs for each value; `contacts.json/CSV`
retains individual observations. These are per-author/topic groups, not verified
person records. Unattributed HTML page contacts are grouped by page and need review.

Supported publishing formats include visible text, mailto/tel anchors, explicit
bracketed email obfuscation, scheme-less LinkedIn profile URLs, WhatsApp links and
labelled numbers, and public JSON-LD email/telephone/sameAs fields. Plain local
phone numbers are captured only when explicitly labelled or linked, and retain
their unknown country code. `00` international prefixes normalize to `+`.
WhatsApp numbers are populated from both explicit labels and supported numeric
WhatsApp links; group-invite links remain links with no invented phone number.
Published WhatsApp numbers also populate the phone field. Phone availability alone
never implies WhatsApp availability. No availability or deliverability guarantee
is made for any coordinate; all four receive the same evidence/review treatment.

Each timestamped run writes `contacts.json`, a nonempty `contacts.csv`, `audit.json`,
and raw fetched response bytes with SHA-256 receipts. SQLite stores deduplicated
observations between runs. CSV is escaped against spreadsheet formula execution;
JSON preserves original normalized values. The run CSV contains this run's results,
not an export of historical SQLite records. Outputs are ignored by this folder's
`.gitignore`; do not publish contact records or raw forum responses accidentally.

- Contacts in supported Discourse threads come only from the topic author's posts,
  not applicants' replies. Explicitly quoted contacts may still belong to someone
  else: ownership always requires human review.
- Default thread coverage is initial posts plus at most two extra batches of 20.
  `source_coverage` reports if later updates were not loaded. Use `--max-batches`
  to expand a specific thread. A comments-closed flag is separate from hiring status.
- HTML-only sites produce unassigned contacts, not verified buyer contacts.
- Phone extraction preserves explicit international numbers and tel/WhatsApp links.
  Unlabelled local numbers in body text are intentionally not guessed. A phone number
  does not prove a WhatsApp account. Published WhatsApp links and numbers explicitly
  labeled WhatsApp are recorded separately; no account-existence check is attempted.
- Unknown posting dates, missing robots, access blocks and fetch failures are
  recorded. No CAPTCHA/login bypass or hidden/private LinkedIn scraping is used.
- Known stale/filled/seller/excluded-territory posts are withheld from contact
  results, with the reason retained in the audit. Text rules are conservative
  heuristics; no automatic eligibility, open-job or production-fit guarantee.
- Region filtering excludes Kolkata/West Bengal mentions, but approved corridors
  and buyer headquarters still require manual verification. Global or unknown
  locations remain flagged for review rather than assigned an invented location.
- `--timezone Asia/Singapore` applies only to a batch whose buyer timezone you
  already know. It records local time and whether it is weekday 09:00–18:00;
  this is a business-hours proxy, not solar daylight or proof someone is online.
  On systems without IANA timezone data, install `tzdata` or omit this option.
- `already_contacted.json` contains the three previously emailed business contacts.
  Pass it via `--suppress-file` to omit them; update it after verified sends.

No SMTP commands, email sends, WhatsApp messages or LinkedIn actions are present.
Use the master prompt in `D:\anonym\FUTURE_AGENT_GLOBAL_LEAD_HUNT_PROMPT.md` to
review ownership, source freshness, buyer fit and evidence before drafting.
