# Forensic Post-Mortem Validation Addendum — 2026-09-24

This addendum corrects the confidence level and execution record in [FORENSIC-POST-MORTEM-ANATOMY.md](FORENSIC-POST-MORTEM-ANATOMY.md). The original report is retained as a hypothesis record; it is not accepted as proof of its proposed Yahoo redirect or content-script root cause.

## Bottom line

The complete 18-lane, all-controls audit is **not complete**. The strongest current finding is a failure boundary, not a machine-level root cause:

- At `2026-09-23T19:38:52Z`, the relay returned `/debug` successfully, but its pinned-tab observation was `299.438783` seconds old, beyond the runner's `120`-second freshness limit. The runner halted before creating a route directive. Run `20260923T193852-be27760f` recorded zero routes and no page action.
- A preceding active attempt, `20260923T191757-e9d2c09c`, stopped at the `/debug` request timeout before any route. Its report has zero route records.
- This establishes why the current audit could not safely proceed: the bridge/relay could not supply a fresh-enough tab observation. It **does not** identify why the heartbeat/observation became stale. CPU saturation, Chrome, the content script, network, or relay scheduling remain possible contributors, not proven causes.
- The observation timestamp did advance between the two dry runs (`19:15:36.996Z` to `19:33:53.033Z`), but was still stale at the second run. That is evidence of intermittent or delayed observation, not proof that the tab was continuously dead.

## Reconstructed 18-lane run

Run `20260923T175558-b1ee254c` planned 18 lanes, ran from `17:55:58Z` to `18:04:43Z`, and recorded **seven** `lane_start` events but only **five** route records in its JSON report. The mismatch is a report-accounting defect. The bounded extension-provided control inventory was explicitly marked as not a full DOM scan.

| Lane | Evidence in the captured run | What it establishes |
|---|---|---|
| Gmail inbox | The starting snapshot marked control execution `NOT_TESTED`. The route's two click probes targeted “Skip to content” and “Using Gmail with screen readers”; both returned `target-not-found-or-not-visible`, with relay status `failed`. | The autopsy's claimed successful “Inbox” and “Snoozed” clicks are contradicted by the route's recorded targets/results. The two failed probes were nevertheless labeled `VERIFIED_CLICK`, a false positive. |
| LinkedIn feed | Open directive was queued; the resulting URL remained Gmail and relay status was `unverified`. | Navigation claim failed verification. The old runner nevertheless advanced to later lanes. Cause not established. |
| LinkedIn messaging | Exact destination and journal receipt recorded as verified. | This route succeeded in that run. |
| LinkedIn service marketplace | Exact destination and journal receipt recorded as verified. | This route succeeded in that run. |
| Yahoo Mail | Directive was served at `18:00:22.174Z`, but no terminal receipt was recorded; the report's observation was timestamped `18:00:21.511Z` and still showed LinkedIn. | The destination was not verified. The snapshot predates the serve by about 0.66 seconds, so it cannot establish what happened after the navigation request. |
| Foundit | Directive queued; later state validation failed with tab-observation age `228.908146` seconds. A `route_exception` wound was written, but no Foundit route record was added. | The tab state had become stale; this alone does not identify why. |
| Naukri | A directive was queued after the Foundit exception; no route result appears in the final route array. | The old runner continued without fresh-state proof; Naukri outcome is unknown. |
| Remaining 11 lanes | No route results in this run. | Not tested. |

The old report's wound summary lists `routes_audited=5`; the JSONL lane-start events show the additional Foundit and Naukri attempts. Foundit's directive was explicitly cancelled as `audit-timeout-before-serve`; Naukri's directive was still `queued` at the final logged check (`18:04:43.176Z`), with no receipt. Do not treat the count as a complete execution ledger, or claim every later directive was tombstoned.

## Claims from the original autopsy that are not established

1. **Yahoo HTTP 302/307 to `login.yahoo.com`: unproven.** The captured audit record has no HTTP status, redirect chain, or observed `login.yahoo.com` destination. The only recorded Yahoo-route observation still points at LinkedIn and predates the directive's served time.
2. **Missing Yahoo login match as the historical root cause: unproven.** The historical run reports bridge `2.26`. The current saved manifest is `2.27` and contains `https://login.yahoo.com/*` and `https://*.yahoo.com/*`; the relay still reported runtime bridge `2.26` during the latest fresh-ish observation. Thus the source now contains the proposed host coverage, but the browser has not yet demonstrated that it loaded that source or that it resolves the historical failure.
3. **A specific stale relay process/PID as the cause: unproven by this run.** The run data does not prove which code was resident in a process at the failure time. A passing unit test does not prove the running process loaded that code.
4. **CPU or memory pressure as the root cause: not established for this event.** Earlier profiling can motivate a controlled correlation study, but no fresh, time-correlated process profile was captured with the `19:38Z` stale observation. Do not name a machine process as culprit from the current evidence.
5. **Click success: the old `VERIFIED_CLICK` label was a false positive.** For LinkedIn “Skip to search” and “Skip to main content,” the extension reported `clicked`, while the relay journal was `unverified` with `action-evidence-insufficient`. The site effect was not measured. The correct conclusion is an extension-reported click outcome with no verified effect—not a verified click.
6. **Full control inventory: not achieved.** The runner records an extension-reported bounded inventory, not every DOM control or every human/automatic click. The original claim of full coverage is not supported.

## Corrective actions made

- The audit runner now fails closed on an unverified route, route exception, stale page observation, or unverified click-continuity barrier. It does not queue the next lane after such a failure.
- Click candidates must be positively classified as safe navigation/expansion controls. Unclassified controls and social/connection actions are excluded.
- Click evidence is labeled as a correlated relay outcome only; `site_effect_verification` remains `NOT_TESTED`. A click claim is never promoted to `VERIFIED_CLICK` from an extension report alone.
- Live execution requires an explicit mode: `--dry-run`, `--live-read-only`, or `--execute-clicks`. A default invocation cannot silently run active page operations.
- The mission plan now pins bridge `2.27`, matching the saved extension source. The runner now checks a fresh tab observation against that pin and fails closed on a version mismatch; previously, `expected_bridge` was only metadata and was not enforced.
- Starting-page observations are recorded separately from route attempts; route exceptions receive route records; the wound summary counts attempted and unattempted routes separately.
- The action ledger now distinguishes planned operations, queued directives, outcome checks actually performed, and site effects not tested. The latest dry run reports `actions_planned=[]`, `actions_attempted=[]`, and `actions_tested=[]`; it no longer claims that it tested `open` merely because that operation was available in the mode.

These are local runner/reporting corrections. They do not constitute a successful live 18-lane run, do not change the loaded extension version, and do not verify site-side effects.

## Latest evidence and current gate

Dry run `20260923T193852-be27760f`:

- `/debug`: HTTP 200 in about 0.35 seconds.
- Pinned tab: Chrome tab `826617425`, runtime bridge `2.26`, URL `https://mail.yahoo.com/c/n/folders/00_1?reason=n8_cloud`.
- Relay `observed_at`: `2026-09-23T19:33:53.033Z`; age at the runner check: `299.438783` seconds; configured maximum: `120` seconds.
- Result: `DRY_RUN_HALTED`, zero route records, zero directives, zero page actions.

After the plan/version guard was corrected, the relay was found stopped: nothing was listening on `127.0.0.1:8778` and no `li_relay.py` process was found. The unit test for port exclusivity uses an ephemeral port (`127.0.0.1:0`), so there is no evidence that the test stopped the relay. I restored the intended local relay in an attached command session; `/health` returned HTTP 200. No browser or account action was taken.

Final dry run `20260923T195352-699d6a4b` then returned `/debug` HTTP 200 but exposed both blockers: the tab observation age was `1200.703772` seconds, and runtime bridge `2.26` did not match the corrected plan's expected `2.27`. It halted with zero routes/directives/actions. The corrected action ledger was empty for planned, attempted, and tested actions. This gives the current reproducible stop condition: stale telemetry plus wrong loaded bridge version, not a proven cause of either condition.

The prior active attempt `20260923T191757-e9d2c09c` timed out at `/debug` and also produced zero route records. Computer UI recovery failed separately (`get_window_state` timed out; the refreshed app listing no longer contained the selected Yahoo Chrome window), so no stale UI handle or coordinates were reused.

## Verification

- Python relay + audit-runner suite: **30 tests passed**.
- Chrome extension Node suite: **7 tests passed**.
- Python syntax compilation: passed.
- The dry run above reproduced the stale-state halt and did not create a directive.

## Remaining work / honest completion status

The instrumentation and false-positive reporting defects have been corrected and regression-tested. The mission is **not** yet complete: no site-by-site audit has been executed with a fresh observation, no full DOM/control inventory has been validated, and no underlying cause for the stale/intermittent bridge observation has been isolated. The next valid live run requires a fresh `observed_at` within the runner's 120-second limit and runtime bridge `2.27`. The local extension source and now-corrected mission-plan pin are `2.27`, but the relay still reports loaded runtime `2.26`; reload the unpacked extension and refresh the pinned tab before treating `2.27` as live evidence. The runner will now reject a fresh snapshot from `2.26`. After freshness and version alignment are restored, rerun the guarded audit serially in the one pinned tab and stop at the first evidence failure.
