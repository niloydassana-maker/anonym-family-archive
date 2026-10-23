# Verification notes

Checked on 23 October 2026 using real public forum data.

- Direct live Wellbayt topic fetch succeeded with zero errors. Five contact
  observations were extracted from six original-author posts. The known published
  buyer email was recovered; author attribution was Alvaro_Zapata only.
- Live recent-topic discovery processed three topics (eight author-post records)
  with zero errors and zero contact candidates. A zero result is retained honestly.
- Extractor component checks against genuine saved public forum JSON recovered
  email, LinkedIn profile and phone fields. The archived samples include applicant
  posts and were used only to check parsing, not certified as buyer leads.
- WhatsApp links and explicitly labeled international WhatsApp numbers are
  implemented, but no such contacts were observed in these checked samples.
- Broad Brave search requires an API key and has not been exercised in this run.
- No messages were sent. No synthetic network data or fake lead records were used.
- Raw fetch bytes, timestamps, hashes and audit records are under output/.

## Four coordinate upgrade verified 23 October 2026

Supersedes the earlier WhatsApp-unobserved limitation for labelled-number parsing.
The real-source regression now recovers all four types from genuine archived
public forum posts: 71 distinct emails, 14 LinkedIn profiles, 7 phone numbers and
4 explicitly labelled WhatsApp numbers. These include applicant posts and are
parser evidence only, not new qualified buyer leads. Source hashes are retained
in output/four_coordinate_verification/regression.json.

A fresh live Wellbayt run succeeded with zero fetch errors and correctly recovered
only the buyer's published email. The new leads.json/CSV record has all four
coordinate fields, author Alvaro_Zapata, coordinate_count 1, and explicit
not_found_in_scanned_content statuses for the other three fields. This also checks
that the script does not invent or cross-associate missing contacts.

The attempted extra live topic /t/315672/85.json returned HTTP 404; it was not
substituted with fabricated content. Broad search still requires an external key.

Re-run: python tools/lead_hunter/verify_real_sources.py --archive war-log/audits/cash-deadline-20261023
