# Complete employment automation: feature scope and proof

This document is the acceptance checklist for the product. “Complete” means the workflow can audit and improve a candidate profile from verified facts, find and score roles on each configured portal, complete an application without inventing answers, and prepare or publish a relevant LinkedIn comment when the operator has approved it. It does not mean bypassing a login, CAPTCHA, portal restriction, or an unknown personal answer.

## Required feature checklist

| Feature | Required behavior | Current implementation | E2E proof |
|---|---|---|---|
| Candidate record | Use one configured resume and private operator-confirmed answers; verify resume hash | `candidate-profile.example.json`, `scripts/apply_answers.example.txt`; local config is required | Launcher preflight; client-specific live proof required |
| Profile audit | Read Naukri, Foundit, Indeed and LinkedIn profile state; find missing or stale fields | Tool-directed procedure in `MISSION-RUN.txt`; current script reads Naukri only | Naukri read receipt exists; other portals not yet audited |
| Profile improvement | Propose truthful headline, summary, skills and experience changes; apply only fields supported by the candidate record; read back and screenshot | Agent360 tool-directed procedure; no dedicated profile-edit runner | Not yet complete |
| Naukri job discovery | Search/recommended results, score resume skills, retain matched and rejected receipts | `scripts/lane_jobs.py` | Launcher lane result |
| Foundit discovery | Search through the live UI, score results and retain receipts | `scripts/lane_foundit.py` | Launcher lane result |
| Indeed discovery | Search, extract actual job cards and apply the same skill gate | `scripts/lane_market_probe.py` | Launcher lane result |
| LinkedIn discovery | Search, extract actual job links and apply the same skill gate | `scripts/lane_market_probe.py` | Launcher lane result |
| Naukri application | Deduplicate against application history, revalidate a live match, answer known gates, submit once, verify portal success | One candidate-specific historical submission is confirmed in portal history | Screenshot receipt `evidence/employment-lane/apply-history-duplicate-20261007105421.png`; not a template or a new client result |
| Foundit application | Open a live matched role, complete supported fields/questions, submit once, verify history/confirmation | Agent360 tool-directed procedure; no dedicated submit runner | Not yet complete |
| Indeed application | Complete Indeed-hosted applications; stop on external employer handoff or unknown required answers | Agent360 tool-directed procedure; no dedicated submit runner | Not yet complete |
| LinkedIn application | Complete Easy Apply steps, answer only known questions, submit once and verify confirmation | Agent360 tool-directed procedure; no dedicated submit runner | Not yet complete |
| LinkedIn feed engagement | Find relevant posts, check for an existing comment, prepare a useful ASCII comment, publish only with explicit send approval, screenshot the posted result | Agent360 tool-directed procedure; no dedicated comment runner | Not yet complete |
| Safety and dedupe | One browser owner; no login/OTP entry, paid upsell, duplicate application/comment, fabricated answer or false DONE | `scripts/lane_tools.py`, `docs/AGENTS-EMPLOYMENT.md`, ledger | Required on every lane |
| Tool-directed mission | Direct the agent to use existing Agent360 browser tools for every portal action; no bespoke portal driver required by the mission | `MISSION-RUN.txt`, `docs/EMPLOYMENT-LANE-MISSION.md` | Prompt is updated; lane-specific live proof remains required |
| Standalone launcher | Package-relative paths, validate local runtime/candidate data, launch the mission agent, preserve output and return nonzero on agent failure | `kilo-bridge-setup.ps1`; `-Launch` dispatches OpenCode with Agent360 MCP and mission files; deterministic lane scripts are not substituted for the agent | Agent mission must be run and audited after these launcher changes |

## Release gate

Do not label the product “complete employment automation” until each row above has a usable tool-directed execution path and a lane-specific receipt. A mission directive is not an implementation receipt. A live-session screenshot or a search result is not proof of profile update, application submission, or comment publication. Unknown personal questions are a legitimate stop and must identify the exact question.

Some actions are deliberately gated at the point of publication: LinkedIn comments require explicit send approval under the house rules; job applications require a current skill match and only operator-confirmed personal facts. CAPTCHA, MFA, account login, external employer redirects, rate limits, and paid services are handled as blockers rather than worked around.
