# Master lead hunter and false positive controls

Run from PowerShell with Python 3.10 or newer:

```powershell
python D:\anonym\tools\lead_hunter\hunt_100_leads_master.py --days 5 --limit 500 --deliverables-dir D:\anonym\deliverables
```

Keep `hunt_leads.py`, `lead_quality.py` and `hn_source.py` alongside the master script. No external
Python packages are required. `--limit 500` caps retained candidates; it does not
promise 500 buyers or increase each source's discovery limits automatically.

The default is now `--contact-policy direct-only`. It is a direct-acquisition
lane: a retained record must publish a purpose-attributable email, LinkedIn,
phone or WhatsApp route in the buyer's own request. `all` then searches only
direct-capable buyer sources: n8n/Make, ERPNext, Directus, Botpress, WeWeb and
Camunda buyer discussions, plus Hacker News freelancer requests. It deliberately
does not burn the scan on crowded application portals or employment boards.

Use `--contact-policy any-route` when you specifically want a separate
marketplace research run. A platform URL never becomes an email, phone or
WhatsApp coordinate. Direct-contact and native-application results are
exported separately.

## Filtering

- Requires an identifiable buyer request or job listing and a specific fit to
  automation, AI workflow, integration, backend or data-pipeline work. Generic
  mentions of AI or engineering in employer boilerplate do not establish fit.
- Rejects known filled notices, seller/help posts, unpaid/applicant-fee offers,
  stale or undated publications, explicit India-ineligible restrictions and the
  user's excluded territories. True UTC dates are used; WordPress uses date_gmt.
- Client location and applicant eligibility are evaluated separately: a US-based
  client is not evidence of a US-only applicant restriction. Unknown territory and
  identity remain visible review flags; no approved-hub location is inferred.
- Recognizes explicit FastAPI MVP and agent setup implementation requests, while
  excluding corporate-trainer-only roles. Identical full briefs with the same
  normalized title are recorded as repost duplicates rather than separate demand.
- Active marketplace status alone does not establish buyer intent: completed-work
  showcases and self-promotional descriptions without a buyer request are rejected.
  Structured listing budgets and amounts written in the brief are retained
  separately; an explicit conflicting budget is flagged before quoting.
- Extracts all four coordinates, preserving per-value source/context. Email,
  LinkedIn, phone and WhatsApp remain separate. A published phone never establishes
  WhatsApp use. Syntax does not prove ownership, assignment or deliverability.
- Rejects accommodation, disability, alternative-assessment, fraud-reporting,
  support, legal/privacy, example and unattributable contact blocks. Quoted
  applicants' contacts are not attributed to the buyer. Missing fields stay missing.
- Suppresses previously contacted buyers using `already_contacted.json`.
- Jobicy's current public engineering feed supports bounded cursor pagination.
  Surviving records are checked using the official listing-status endpoint.
- Make discovery uses its public Looking for an expert category (74), not the
  robots-disallowed search endpoint or seller-offers category. n8n and ERPNext
  use their Jobs categories; Directus, Botpress, WeWeb (Jobs & collabs category)
  and Camunda use their public category or recent-topic feeds. Expanded on
  23 October 2026 with live-probed feeds that return usable public JSON under
  standard Discourse robots (allows /c/ /t/ /u/; disallows /search): Bubble
  Jobs/Freelance, Retool latest, Hugging Face latest, LangChain latest,
  NocoDB latest, Baserow latest. breadth_depth_urls.txt was extended with
  140+ recent buyer-like topic URLs from Bubble and WeWeb for explicit
  --urls-file runs. Earlier candidates (Appsmith, Windmill, Flowise,
  Pipedream) remain disabled where feeds 404, non-JSON or robots-blocked.
- Direct-only mode uses the providers' permitted Jobs / Looking-for-an-expert
  category feeds. Their public search endpoints are currently robots-disallowed,
  so the hunter does not query or bypass them.
- Hacker News discovery uses Algolia and verifies each retained top-level employer
  comment and its thread through the official Firebase API. Only official
  `whoishiring` hiring/freelancer threads qualify; applicant replies, seeking-work
  posts and dead/deleted records are excluded. The comment itself must satisfy
  the requested age limit. Employment-only contacts are not service-pitch targets.
- Jobspresso, RemoteOK and WWR matches with unresolved hiring liveness remain in
  quarantine. Unknown Jobicy status, unclear India eligibility, incomplete forum
  coverage, and multiple possible personal profiles are also quarantined.
- Shared coordinates/source URLs are deduplicated without merging personal
  identities or copying coordinates between unrelated records.

No automated extractor can guarantee zero false positives or verify every owner's
identity. This tool does not label output as verified buyers or send-ready contacts.
`OUTREACH_READY.json` remains empty until a human verifies each intended recipient,
contact purpose, current opportunity and eligibility. No messages are sent.

## Sources and limits

Sources: Hacker News, Jobicy, Jobspresso, RemoteOK, We Work Remotely, Freelancer
public projects and owner labels, n8n Jobs, Make Looking-for-an-expert, Bubble
Jobs/Freelance, WeWeb Jobs & collabs, plus latest feeds from Retool, Hugging Face,
LangChain, NocoDB, Baserow, Directus, Botpress, Camunda and ERPNext. These include
both project requests and employment listings; employment is not a guarantee of
next-week cash.

Freelancer discovery now includes thirteen focused queries: n8n, Make.com,
LangGraph, FastAPI, webhook, email automation, Stripe integration, AI agent,
Python automation, API integration, CRM automation, workflow automation, and
WhatsApp Cloud API. Results still pass the same recency, status and fit gates.
`--sources hn` and `--sources freelancer` support focused runs.

Default limits: 5 days, maximum 500 retained candidates, 30 forum topics total,
10 pages per paginated job feed, two extra forum batches of 20 posts, 600 JSON/text
request attempts plus robots requests, and 0.5-second request spacing. Discovery
is bounded, not an exhaustive worldwide scan. Use `--help` to change limits.
Provider access restrictions are respected and failures are recorded.

Explicit `--url` or `--urls-file` inputs replace default forum discovery. Use
`--sources discourse` for forum-only runs. API errors and interrupted scans retain
partial results. No account logins, credential discovery or bypassing blocks.

To run a broader, explicitly portal-inclusive research pass:

```powershell
python D:\anonym\tools\lead_hunter\hunt_100_leads_master.py --contact-policy any-route --days 5 --limit 500 --deliverables-dir D:\anonym\deliverables
```

## Outputs

Every run writes `output/master_<UTC timestamp>/` and optionally copies report
files into a uniquely named subfolder of `--deliverables-dir`.

- `MASTER_500_LEADS.json/CSV` and `MASTER_100_LEADS.json/CSV`: compatible aliases
  containing the same source-filtered review candidates, capped by --limit.
- `MASTER_500_LEADS_REPORT.md` and `MASTER_100_LEADS_REPORT.md`: same review report.
- `DIRECT_CONTACT_LEADS.json`: candidates with at least one purpose-attributable
  published email, LinkedIn, phone or WhatsApp coordinate.
- `PLATFORM_APPLICATION_LEADS.json`: candidates with native application routes and
  no public personal coordinates. These remain useful opportunities, not SMTP leads.
- `quarantine.json`: unresolved source/eligibility/ownership records.
- `rejected_coordinates.json`: disallowed contact observations with context/reason.
- `duplicates.json`: suppressed duplicate-source or shared-contact observations.
- `OUTREACH_READY.json`: deliberately empty until human verification.
- `audit.json` and `evidence/`: options, exclusions, errors, actual raw responses and
  SHA-256 receipts. Hashes certify saved bytes, not buyer legitimacy.

CSV cells are escaped against spreadsheet formula execution; JSON preserves values.
Historical outputs are retained as evidence, not certified or reissued. Older
reports containing accommodation/support contacts should not be used as a contact
list; consult only a newly filtered run and its audit.

Exit codes: 0 completed without request errors (possibly zero candidates);
2 request/argument errors; 130 interrupted with partial results.

## Verification

From the script directory:

```powershell
python -m unittest test_master_real_sources test_false_positives_real_sources test_contact_purpose_real_sources test_real_application_routes test_direct_lane_real_sources -v
```

All nineteen checks passed on 23 October 2026, using genuine saved forum/API records
without mocked APIs or manufactured lead fixtures. The tests cover the known
Gartner/Mozilla/Fastly accommodation contacts, unrelated roles, NFQ PHP mismatch,
WordPress date handling, ClickUp support/fraud-reporting routes, LaunchDarkly fraud
reporting, DuckDuckGo's alternative selection-process address, four-coordinate
parsing, legitimate Wellbayt contact evidence and suppression, and valid exports.
Positive checks also retain real native applications, distinguish US client
location from residency restrictions, accept actual FastAPI/agent implementation
briefs, reject a trainer-only role, and collapse an identical live repost.
They also reject two actual marketplace showcases and flag an actual budget
discrepancy instead of presenting either amount as an agreed contract.
The direct-lane check excludes an actual closed marketplace invitation even though
it publishes an email address, so a visible coordinate alone cannot create a lead.
Test evidence requires the local historical output/archive folders referenced by
the test files. It does not establish a guarantee against new unseen false positives.

Source documentation:
https://jobicy.com/jobs-rss-feed
https://weworkremotely.com/remote-job-rss-feed
https://github.com/HackerNews/API
https://hn.algolia.com/api
