# Employment Lane Agent Rules

Use this package with the current operator's configured candidate profile and authenticated
browser session. Do not assume a specific candidate identity, Windows account, Chrome profile,
or local installation path.

## Browser tools

All browser actions must use the configured Agent360 browser MCP tools:

- `browser_navigate`, `browser_click`, `browser_click_xy`, `browser_fill`
- `browser_press_key`, `browser_wait`, `browser_execute_script`
- `browser_get_page_content`, `browser_screenshot`
- `browser_list_tabs`, `browser_switch_tab`, `browser_close_tab`

Do not use direct CDP, Playwright, Selenium, a separate debug Chrome, or a second browser
driver. Only one Agent360 client may drive the authenticated browser at a time. If the current
session is unavailable, stop and report the blocker instead of opening a new profile.

Take a screenshot first when needed to bind the extension. If `browser_list_tabs` is empty,
bind with a screenshot before treating that as a missing tab. `browser_execute_script` uses
expression form; read page state before navigating, because blind navigation can replace a
useful page or interrupt its load. If a tool returns empty output or times out, treat it as an
interrupted/failed action until a fresh read proves the state.

## Candidate facts and account access

- Use only the resume configured in `candidate-profile.json` and verify its SHA256 before use.
- Use only verified candidate skills and explicitly candidate-confirmed answers from the
  configured private answer file or current conversation. Never transfer facts between
  candidate profiles or infer missing experience, dates, degrees, employers, or certifications.
- Never request, read, or enter passwords or OTPs. Do not change account security settings.
  If login, MFA, CAPTCHA, or human verification appears, stop that portal and report it.
- Never make a purchase. Dismiss paid upsells only when the visible UI offers a safe way to
  continue without buying.

## Applying and public actions

- Check application history before applying. Match the exact job title and employer, and
  inspect the nearby status; unrelated page-wide words do not establish a duplicate.
- Apply only to a current role that passes the configured fit gate. Verify the live title,
  employer and form before entering answers. Stop on an unknown required answer, portal limit,
  external-site handoff, or ambiguous submit state. Never retry an ambiguous submission.
- If an apply panel closes after Save/Continue, inspect the portal's application history and
  verify the exact role, employer and sent/applied status before recording `APPLIED`.
- LinkedIn public comments must be truthful, relevant, one per post, ASCII, and contain no
  links, pricing, catalogue/demo reference, or self-promotion. Prepare a draft, but do not
  publish it unless the exact final text has explicit `SEND-APPROVED` authorization.

## Evidence and reporting

- A tool response is not proof. Screenshot the visible result after profile changes,
  applications and comments; record a ledger row for each meaningful action.
- Record only actual jobs, not page fragments such as dates, locations, filters, Save buttons,
  or employer names. Confirm title and employer from the visible card or job detail page.
- Use `APPLIED` only after visible portal confirmation or exact application-history status.
  Record ambiguous/unverified work as `BLOCKED`; record a mismatch as `NO_MATCH`.
- End each run with profile changes, confirmed applications, blockers, skipped work, and the
  ledger path. Keep package feature-coverage status aligned with receipts; a prompt directive
  or a green search run does not prove an application, profile edit, or public comment.
