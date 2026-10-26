# Funding-filter audit, 26 October 2026

## Result

Read-only inspection of **32 recently rejected issues**, plus **8 issues outside
the two-comment search cap**, found **no new actionable, funded, uncontested
task in this sample**. This is a targeted sample, not evidence that the market
has no work or that every filter is correct.

The audit did find a misleading rejection diagnostic. Some issues contain a
parsed monetary amount but lack recognized payer authority or bounty attestation.
The dispatcher described that case as a missing amount. Its message now names
the authority/attestation condition. Acceptance rules, amounts, floors, comment
limits, authority checks, and competition rules are unchanged.

## Method and evidence

Evidence was captured around 23:20–23:25 IST from GitHub's live issue and comment
APIs and production lookup functions. No messages, proposals, claims, or PRs were
sent. No delivery database state was changed.

The rejection sample prioritizes recognizable bounty hosts, payment platforms,
and recent records, with at most two issues per repository. For each issue the
audit saved the full API issue and all paginated comments, compared the
production comment fetch with the complete recognized-author/platform comment
set, and reran the live eligibility gate. Relevant candidates also received
competing-PR checks. The API reads completed without errors for all 40 issues.

Receipts are local under `scratch/audit-funding-20261026/`:

- `audit-receipt.json`: 32 rejected issues, full-input artifact names and SHA-256.
- `high-comment-summary.json`: a separate 40-result search probe above the comment cap.
- `high-comment-details/audit-receipt.json`: 8 selected issues fetched in full.
- `competition-receipt.json`: additional live PR checks.
- `diagnostic-replay.json`: all 40 eligibility booleans unchanged after the message fix.
- `verification.json`: all five existing local verification suites passed with
  `python -W error`; compilation exited 0 with empty stderr.

These raw public-source artifacts remain outside Git. No credentials are included
in this report or the commit.

## Findings from the 32 rejected issues

- **All 32 remained ineligible** after retrieving complete comments. The
  production and complete recognized comment sets had equal counts throughout
  this sample.
- **29 had no parsed monetary amount.** Many were requests to integrate Polar
  subscriptions, payment infrastructure, or an Algora discovery feature, rather
  than offers to pay for the implementation.
- **Three had amounts but still failed the gate.** Their previous generic
  rejection wording obscured this distinction.

| Issue | Live evidence | Disposition |
| --- | --- | --- |
| [Gitpay #1614](https://github.com/worknenjoy/gitpay/issues/1614) | Reporter entered a $150–$250 bounty range; no recognized payer authority. Live check also found [PR #1617](https://github.com/worknenjoy/gitpay/pull/1617). | Keep excluded. |
| [Gitpay #1615](https://github.com/worknenjoy/gitpay/issues/1615) | Same authority distinction; live check found [PR #1618](https://github.com/worknenjoy/gitpay/pull/1618). | Keep excluded. |
| [Omi #23467](https://github.com/BasedHardware/omi/issues/23467) | Contributors ask about past compensation and previously proposed $50–$200 amounts. This is not a new commissioned implementation. | Keep excluded. |
| [ParaSpell #2318](https://github.com/paraspell/xcm-tools/issues/2318) and [#2285](https://github.com/paraspell/xcm-tools/issues/2285) | Bug-bounty labels, but no parsed issue reward amount. No open competing PR was found at capture. | Potential manual funding/eligibility review, not verified automatic work. |

The ParaSpell template also has contributor eligibility and human-authorship
conditions; a bounty label alone is not proof that this automated workflow can
claim a reward.

## Probe above the two-comment cap

Two of the eight detailed candidates passed the existing funding gate, but both
had open competing PRs:

- [microG #2843](https://github.com/microg/GmsCore/issues/2843), the WearOS bounty:
  the live checker found [PR #3918](https://github.com/microg/GmsCore/pull/3918).
  The task additionally requires physical-device acceptance and disallows AI
  agent engagement. It is not suitable work for this fleet.
- [Startup Credits #241](https://github.com/sourcey/startup-credits/issues/241):
  the live checker found [PR #2013](https://github.com/sourcey/startup-credits/pull/2013).
  Manual inspection also showed that $400 refers to Polar's subscription price,
  not an offered implementation reward. This exposes a potential **false
  positive** in monetary-context recognition; it does not establish missed income.

Another [subscription-pricing issue](https://github.com/isaacalbala12/Vantare-Simracing-Suite/issues/1620)
in the broader search probe also passed a body-only gate using product prices.
This was not advanced as a bounty. Relaxing the comment cap alone would increase
this risk without demonstrating new eligible work in the inspected sample.

[pgstrap #2](https://github.com/seveibar/pgstrap/issues/2) exposed a comment-fetch
limitation: the production keyword shortcut fetched no comments, while the full
audit recognized nine. Complete evaluation still rejected it for payment
negation, and its parsed $30 was below the live $50 floor. Therefore this is a
mechanism to investigate further, not a confirmed lost qualifying task.

## Decision

Keep the funding, authority, and no-competing-PR gates unchanged. Do not classify
all rejection messages as evidence of absent payment: use the corrected reason
and inspect context. Do not count product subscription prices as rewards.

The current sweep is still progressing through a 1,000-result horizon for each
query, so the task feed is also limited by sequential scan time. A useful next
optimization is to scan the newest page across all queries before deep backlog
scans, while retaining the same eligibility checks and complete-payload transport.
This audit did not change scan scheduling, widen filters, restart the dispatcher,
or interrupt active Kaggle work. The diagnostic change applies when the next
dispatcher process loads the updated source.
