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

## Initial repair and follow-up query regression

The first repair added `no:assignee` and `-linked:pr`, but wrapped each complete expression
in parentheses to try to bind those qualifiers across `OR` branches. The live run
[`40598151541`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40598151541)
completed successfully yet reported zero raw hits in all four lanes. That was not an influx
receipt.

Comparing the exact query against GitHub Search isolated a query-compilation regression:
the run's grouped `bountyhub-bot` query reported zero, while the same expression without
the wrapper returned five issues through the live REST search API. A second live comparison
changed `bounty in:title` from 10,976 results unwrapped to 60,247 wrapped. The parentheses
changed REST search semantics, so the initial fix was not considered successful.

The follow-up compiler in `actions_dispatch.py` no longer wraps expressions. It splits
top-level `OR` branches outside quoted text and runs each branch as its own GitHub search,
appending every shared qualifier (`is:issue`, `is:open`, `is:public`, `archived:false`,
`-label:type/experiment`, `no:assignee`, and `-linked:pr`) to each branch before search
results return. It unions and deduplicates the branch results and records the exact query and
per-branch counts in the receipt. A saturated branch keeps the creation-time partition open
for subdivision; results are not dropped to fit a merged count.

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
- The run's grouped `bountyhub-bot` query returned zero; the same query without the wrapper
  returned five through GitHub's live REST API.
- A live global `bounty in:title` query returned 10,976 unwrapped and 60,247 wrapped. These
  are raw search counts, not qualified or dispatched task counts; they show that the
  wrapper changed the query rather than preserving its meaning.
- Some intermediate probes received a secondary rate limit. After it cleared, the grouped
  queries and their unwrapped equivalents were compared against the live REST API as
  described above.

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

- `python -W error -m py_compile scripts/actions_dispatch.py scripts/discovery_horizon.py` -
  passed.
- `python -W error scripts/test_actions_migration.py` - 32 passed, 1 Windows-specific skip.
- `python -W error scripts/test_dispatcher_horizon.py` - 16 passed.
- `python -W error scripts/test_queue_ordering.py` - 20 passed.
- `python -W error scripts/test_icu_pipeline_suite.py` - all 16 sections passed, 100% green.
- Runtime smoke check verified quoted `OR` text is not split, both branches receive every
  shared qualifier, branch results are unioned, and per-branch totals are retained.
- Running the branch-aware compiler against GitHub's live REST API for
  `bountyhub-bot is:issue is:open` produced `branch_counts=[5]`, three returned issue rows,
  and `saturated=false`. GitHub's reported total and returned item count differed in this
  response, so the total is recorded as a search receipt, not as three or five qualified
  tasks.
- `git diff --check` - passed.

The follow-up branch-aware compiler is verified locally and has a live REST query receipt.
Its next Actions discovery receipt is still required to establish deployed candidate flow;
the zero-hit run above remains a failed regression receipt.
