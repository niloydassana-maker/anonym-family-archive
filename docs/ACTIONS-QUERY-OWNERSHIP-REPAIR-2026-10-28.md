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

## Second live regression: OR branches lost their shared context

The first branch-aware compiler still had a supply bug. It split
`label:bounty "auth" OR "permission" OR "unauthorized" is:issue is:open` into three
queries, but only the first retained `label:bounty`; the last query also alone retained the
trailing issue qualifiers. In live discovery run
[`40602001407`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40602001407),
the fresh branch totals were `[1, 66696, 11774]`. The second branch had become a global search
for “permission”, and the third a global search for “unauthorized”. Its non-fresh search
stopped after a saturated branch and recorded `[35, 761471]` before subdividing the horizon.

The compiler now carries the leading shared context and trailing search qualifiers into every
alternative. A live REST comparison with the same filters now returns branch totals
`[35, 34, 5]` for `label:bounty` plus `auth`, `permission`, or `unauthorized`. Another repaired
query, `label:bounty "tool" OR "function calling"`, returns `[134, 0]`. The compiler still
searches each branch independently and unions duplicate issues; it does not use a parenthesized
whole query.

The contextual compiler was subsequently deployed and exercised in Actions run
[`40603676054`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40603676054);
the per-branch query and supply outcome are recorded below.

This repair only changes search scope and cache policy version. It does not change the payer,
engineering, repository-intent, or competition gates. Run `40602001407` had raw lane counts
`programs=36`, `normal=83`, `startup=142`, `founder=5`; its bounded sample recorded 31
`CURRENT_ISSUER_OFFER_MISSING`, 43 `HARD_ISSUE_EVIDENCE_MISSING`, 4 closed/read-only,
4 by-design, and 3 mirror/non-engineering refusals. It qualified and dispatched zero tasks.
That is evidence of continued supply noise, not a quality-approved task receipt.

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
- `python -W error scripts/test_dispatcher_horizon.py` - 16 passed.
- `python -W error scripts/test_queue_ordering.py` - 20 passed.
- `python -W error scripts/test_icu_pipeline_suite.py` - all 16 sections passed, 100% green.
- `python -W error scripts/test_actions_migration.py` runs 34 tests: 33 passed and the
  Windows-only newline-path case skipped. New tests verify common prefix/suffix retention in
  all alternatives and preserve `OR` inside quoted text.
- Runtime smoke check verified quoted `OR` text is not split, every branch retains shared
  context and server qualifiers, branch results are unioned, and per-branch totals are retained.
- Running the branch-aware compiler against GitHub's live REST API for
  `bountyhub-bot is:issue is:open` produced `branch_counts=[5]`, three returned issue rows,
  and `saturated=false`. GitHub's reported total and returned item count differed in this
  response, so the total is recorded as a search receipt, not as three or five qualified
  tasks.
- `git diff --check` - passed.

## Deployed contextual-branch receipt

Actions run [`40603676054`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40603676054)
completed successfully on `b99eb70899824472302742fb1e1394a84a7c0d1e`. Its founder-lane
search log recorded the expression:

```text
"/bounty" mcp OR "model context protocol" is:issue is:open
```

The deployed compiler expanded it into two independent queries, each retaining `"/bounty"`,
`is:issue`, `is:open`, `is:public`, `archived:false`, `no:assignee`, and `-linked:pr`. The
historical date partition returned `branch_total_counts=[0,0]`; the seven-day query returned
`fresh_branch_total_counts=[125,8]` and 33 items, with `saturated=false`. That is a live
query execution receipt, not 133 qualified issues.

The same run's final receipt was `qualified_fresh=0`, `qualified_unique=0`,
`dispatched=[]`. It recorded 31 `HARD_ISSUE_EVIDENCE_MISSING`, 22
`CURRENT_ISSUER_OFFER_MISSING`, three by-design declarations, two closed/read-only issues,
and one mirror/non-engineering item. The query repair is deployed and verified; the influx
plus quality delivery goal is still open because this cycle produced no qualified task.

The next cursor rotation, Actions run
[`40605520311`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40605520311),
also completed successfully on `a1b1a60`. Its raw lane counts were `programs=26`,
`normal=31`, `startup=271`, and `founder=207`. The `/reward` query returned 68,655 historical
matches (4,982 in the seven-day query); its historical window was saturated and returned no
hydrated rows in that partition, so it remains for horizon subdivision. The bounded admission
sample logged 29 `CURRENT_ISSUER_OFFER_MISSING`, 28 `HARD_ISSUE_EVIDENCE_MISSING`, and three
by-design refusals. Final counts remained `qualified_fresh=0`, `qualified_unique=0`,
`dispatched=[]`, with 5,890 pending hydration rows. This is continued raw influx, not a task
or PR success receipt.

## Current funding-program eligibility check

A live REST read of `Expensify/App#105168` found the issue open with title `[$175]`, but it
currently has two assignees. The deployed `no:assignee` search qualifier therefore correctly
excludes it from new work. Its presence in the prior historical admission audit is not a live
dispatch receipt.

The existing Expensify fast-lane query uses a `$250` title term, while the documented programme
checks any `[$N]` title. A trial query keyed only on `commenter:melvin-bot[bot]` returned 96 raw
open/unassigned results; a sample included ordinary FullStory and exploratory issues, so the
commenter qualifier alone is too broad to replace the fast lane. Adding `label:External` to
that trial reduced it to zero current rows. Separately, live queries for unassigned open
Expensify issues with `[$175]` and `[$250]` titles both returned zero. The broad, rotating
`repo:Expensify/App label:External` program query remains in the global program lane, so the
fast-lane `$250` term does not narrow the full search horizon. No gate or admission check was
changed in this experiment; the low-precision trial was discarded.

The distinction is material: GitHub's native query language can filter metadata and match
terms, but a commenter match cannot prove that a specific comment contains a current
maintainer-authorized offer. The dispatcher still verifies the actual amount, offer source,
engineering evidence, repository intent, and competition before dispatch.
