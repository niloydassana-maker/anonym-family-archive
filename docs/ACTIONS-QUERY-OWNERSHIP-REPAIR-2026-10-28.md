# Query-time ownership filter repair - 2026-10-28

## Incident and root cause

Discovery run [`40595663648`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40595663648)
dispatched `Expensify/App#101616` as delivery run
[`40596131378`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40596131378).
The delivery completed without publishing a PR: its preparation receipt correctly refused
the issue because its fix was already merged and shipped in PR #103877. That is a discovery
quality regression, not a successful delivery.

The live GitHub issue was still open, had three assignees, and carried a maintainer-bot
comment saying the fix shipped in version 9.5.23-3. PR #103877 was merged at
`2026-10-26T17:34:41Z`; the issue remained open for its payment-period workflow. The PR
does not close the issue through a GitHub closing reference, so `-linked:pr` alone does not
remove it. The earlier discovery query also had no assignment qualifier.

## Repair

`actions_dispatch.py` now compiles every lane expression inside parentheses and appends the
shared GitHub search qualifiers, including `no:assignee` and `-linked:pr`. Grouping keeps the
shared filters attached to every `OR` branch. Search receipts now record the exact full and
fresh queries sent to GitHub.

The query-policy fingerprint changes with this filter set. On first use, the dispatcher
revisits cached rows, deletes stale candidate snapshots, and retires cached search rows with
assignees so an old Actions cache cannot bypass the new server-side filter. If GitHub later
returns the issue after it becomes unassigned, the row is eligible for hydration again.

## Live evidence

- `GET /repos/Expensify/App/issues/101616`: state `open`; three assignees.
- `GET /repos/Expensify/App/pulls/103877`: merged; `merged_at=2026-10-26T17:34:41Z`.
- GitHub issue search for `repo:Expensify/App 101616 is:issue is:open` returned issue #101616.
- Adding `-linked:pr` still returned #101616, confirming the merged PR was not represented as
  a closing-reference link.
- Adding `no:assignee -linked:pr` returned zero results for that exact issue query.
- The exact grouped query form emitted by the repaired builder also returned
  `total_count=0` for #101616. The grouped paid-program query returned zero unassigned
  matches for its current `$250`/External/Bug slice.
- The representative global startup query remained broad in the live count probe: 77,039
  results before the new qualifiers and 60,249 after them. Those counts are search
  totals, not qualified or dispatched task counts.
- Some intermediate probes received a secondary rate limit. After it cleared, the grouped
  query emitted by the repaired builder was verified live as described above.

GitHub documents `no:assignee` as the unassigned-issue filter and `linked:pr` as issues linked
to a pull request by a closing reference:
[official issue search filters](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests).

## Scope and limitation

GitHub Search can apply built-in metadata qualifiers, but it cannot execute arbitrary Python
admission functions inside GitHub's search service. In particular, `linked:pr` does not find
every PR URL or issue-number mention in comments. Funding authority, amount, hard engineering
scope, repository payment history and other evidence-based checks remain in the existing
dispatcher admission contract; they have not been weakened. This repair prevents the observed
assigned task from entering the queue and excludes formal closing-reference PR links at
search time. It does not claim that every possible merged-PR mention can be expressed as a
native GitHub search qualifier.

## Local verification

- `python -W error -m py_compile scripts/actions_dispatch.py` - passed.
- Query-builder, `OR` grouping, assignee recognition, and cached-row migration smoke check -
  passed against the modified module.
- `python -W error scripts/test_actions_migration.py` - 32 passed, 1 platform-specific skip.
- `python -W error scripts/test_queue_ordering.py` - 20 passed.
- `python -W error scripts/test_icu_pipeline_suite.py` - all 16 sections passed.
- `git diff --check` - passed.
