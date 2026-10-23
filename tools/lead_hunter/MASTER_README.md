# Master lead hunter

`hunt_100_leads_master.py` returns up to 100 recent public buyer-request candidates.
It uses the shared four-coordinate extractor in `hunt_leads.py`; keep both files
together. Python 3.10+ and standard library only.

## Run

```powershell
python D:\anonym\tools\lead_hunter\hunt_100_leads_master.py
python D:\anonym\tools\lead_hunter\hunt_100_leads_master.py --sources discourse --urls-file D:\anonym\tools\lead_hunter\prioritized_fresh_urls.txt --max-topics 120 --max-requests 400
python D:\anonym\tools\lead_hunter\hunt_100_leads_master.py --sources freelancer --query n8n --per-query 10
```

Defaults: last 14 days, up to 30 forum topics, 150 JSON request attempts, two
extra reply batches per thread, 1.5-second request spacing. Robots requests can
add network calls. Partial thread coverage and API/profile failures are recorded.
Discovery reads the latest n8n Jobs category and date-filtered Make hiring search;
it is not an exhaustive search of every forum page. Explicit URL lists replace
forum discovery. `--days` controls true posting age; topic IDs are never used as
timestamps. `--limit` changes retained output count, not discovery breadth.

The default `already_contacted.json` suppression list excludes matching buyers.
Unknown locations require manual corridor verification; excluded locations are
rejected when found in the brief or public owner/profile location. No region,
company affiliation, real identity or messaging permission is guessed.

## Output and migration

Each run creates `output/master_<UTC timestamp>/` containing:

- `MASTER_100_LEADS.json` and `.csv`: four coordinate columns, statuses, count
  from zero to four, per-value evidence/source URLs, public profile URL, flags.
- `MASTER_100_LEADS_REPORT.md`: review candidates, not certified active buyers.
- `audit.json`: fetched byte hashes, response files, exclusions, errors, options.
- `evidence/`: authentic response bytes. Keep these local.

Prior dated reports are preserved rather than overwritten or silently certified.
Old `exclusivity_tier` and `exclusive_channel` claims are removed. `contact_route`
describes the actual source route. `buyer_website` and `buyer_profile_url` are
separate. `can_direct_message` is null unless a forum response explicitly supplies
the permission for that request context. A Freelancer profile never proves DM access.
Verified email/phone status flags on the marketplace are not actual contact values.

Amounts mentioned in forum prose remain unclassified original-post amounts;
they may be rates, quoted examples or fees, not an established project budget.
Freelancer budget fields preserve supplied currency and project type. Marketplace
communications/payment remain subject to platform rules, including when a brief
happens to publish contact details.

Only topic-author posts and public profiles are enriched; applicant replies and
quoted blocks are not used as buyer contact evidence. Missing fields stay missing.
No address generation, login bypass, messages or verification probes are performed.
CSV cells are escaped for spreadsheet formula safety. JSON preserves original values.

Exit codes: 0 = completed without request errors (possibly zero candidates),
2 = request/API errors with audit and partial results, 130 = interrupted with
partial results. Invalid arguments use argparse exit code 2. Ctrl+C preserves
already collected leads even when interrupted during a source harvest.

## Verification of the repair

Four regression checks use actual archived forum responses, without generated
API fixtures or mocked network results. From this folder:

```powershell
python -m unittest test_master_real_sources -v
```

They cover all four contact coordinates and statuses, a buyer's filled notice,
author attribution and prior-contact suppression, and valid empty exports. The
archive at `D:\anonym\war-log\audits\cash-deadline-20261023` must be present.

A bounded live check on 23 October 2026 used Wellbayt and two actual Freelancer
projects, including the public owner endpoint. It completed without request errors,
retained two platform review candidates and rejected the known contacted buyer.
Evidence: `output/master_20261023T102446093617Z/audit.json`. This limited check does
not establish exhaustive worldwide coverage, awards, ownership or payout timing.

The pre-repair source backup is `output/master_repair/original.py`.

Public Freelancer API parameter reference:
https://github.com/freelancer/freelancer-sdk-python/blob/master/examples/get_projects.py
