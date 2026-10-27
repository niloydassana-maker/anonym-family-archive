# Global bounty index and live search audit — 27 October 2026

## Purpose and boundary

GitHub issue search accepts documented keywords and qualifiers; it does not provide a way to run the project's payment, payer-authority, territory or competing-PR functions inside GitHub's search engine. Its REST search API returns at most 1,000 results per query. The custom index evaluates those checks while ingesting GitHub results and exposes only recent candidates that passed them. This is an external search layer; it does not turn those checks into GitHub server-side functions.

An offer in a GitHub issue is evidence of an offer, not proof that funds are escrowed or that a submission will be accepted. A pre-dispatch refresh is still required because issues, comments, payments and PRs can change after indexing. Matching PR titles, bodies, branch names and issue timeline links cannot prove that no unreferenced competing work exists.

## Live audit

At 22:08–22:12 UTC on 26 October, authenticated, read-only GitHub API queries returned:

| Global public, open, non-archived issue query | GitHub total count |
| --- | ---: |
| All issues | 55,866,921 |
| `bounty` | 76,839 |
| `bounty comments:<=2` | 56,610 |
| `bounty comments:>2` | 20,229 |
| `label:bounty` | 4,316 |
| `commenter:algora-pbc` | 32 |

These are GitHub's reported search counts, not the number of paying, available engineering tasks. Search indexes change, and overlapping queries cannot be added as independent opportunities. Of the 32 Algora-commenter results returned in full, 31 had more than two comments and would be outside the dispatcher's current global two-comment query cap. That establishes a coverage loss, not that those 31 are all eligible.

Read-only checks found genuine offer signals with competing PRs: [Crystal-PDF issue 3](https://github.com/iii123iii/Crystal-PDF/issues/3) states $100 and has [open PR 139](https://github.com/iii123iii/Crystal-PDF/pull/139); [SpaceApp issue 64](https://github.com/oll4com/spaceapp/issues/64) has a maintainer comment stating a $400 bounty and multiple open PRs. [Mairix issue 29](https://github.com/rc0/mairix/issues/29) has an older $150 platform notice, subsequent cancellation/uncertainty and open PRs. The index must not present these as clear, uncontested opportunities.

The previously dispatched `anmolkumar912331-oss/javascript-learning#1` contains an HTML page. A live recheck deferred it for lack of a qualifying explicit offer; the previous dispatcher had parsed a page amount as payment evidence.

For [Rowy issue 1527](https://github.com/buildship-ai/rowy/issues/1527), a repository member wrote [`/bounty $50`](https://github.com/buildship-ai/rowy/issues/1527#issuecomment-1920510709). The older authority gate rejected the offer because the issue author was a contributor. The index now carries the verified commenter's association through the authority check. A fresh check reached the competition check and held the issue because [PR 1611](https://github.com/buildship-ai/rowy/pull/1611) is open. This is a live receipt of improved recall and a retained competition gate, not an available task.

The fleet ledger records successful delivery for [Paraloom PR 1233](https://github.com/paraloom-labs/paraloom-core/pull/1233) and [PR 1234](https://github.com/paraloom-labs/paraloom-core/pull/1234). A fresh GitHub API check returned both as open with empty check-rollup arrays. Merge, payment, and the current state of their underlying offers are not established by those delivery receipts.

Detailed raw API responses and summaries are local under `scratch/global-discovery-audit-20261027/`. They contain public issue material and are not committed with this report.

## Implementation and local operation

`scripts/bounty_candidate_index.py` implements a SQLite index, global GitHub search, explicit offer evidence, bounded comment and PR pagination, linked-PR timeline checks, current policy checks, stale-result expiry and rule-source fingerprints. An issue with incomplete evidence is retained for retry and cannot appear in the qualified search. Search partitions use inclusive creation-time ranges; ranges above 1,000 results split into two persisted ranges. Independent query lanes rotate rather than starving the global lane. An `extend` operation adds later creation windows.

`scripts/indexed_fleet_dispatcher.py` previews index results by default. Its explicit `--live` mode refreshes each candidate and then invokes the existing fleet dispatch gate. A live-mode invocation with an empty qualified list returned `outcomes: []`; it did not enqueue a candidate. No live qualified-candidate handoff has been proven in this audit.

`scripts/bounty_index_scout.py` runs bounded read-only GitHub discovery cycles against a seeded index. It alternates lanes and newer/older partitions, retries a limited number of incomplete checks, and stops when a candidate appears. It does not dispatch work. A single live cycle successfully split an additional global range and reported an empty qualified set. At 04:13 IST, a separate 20-cycle scout was started as PID 14452; its live output is in `scratch/global-discovery-audit-20261027/scout.stdout.log`. This is a bounded search process, not an automatic PR or fleet dispatcher.

The live global partition root returned 55,863,549 open issues; subsequent real query counts split it into time ranges until the newest range contained 912 results. A separate `bounty` root returned 76,837 matches and reached a 633-result range. These counts are snapshots, not proof of complete coverage. A funded-label page with four incomplete checks advanced only after recording each error; a subsequent live retry resolved one page-cap error. In the sampled indexed records, the qualified list was empty. That result is not evidence that the global market has no opportunities.

Example commands from the workspace root:

```powershell
python scripts/bounty_candidate_index.py --db scratch/global-discovery-audit-20261027/global-index.sqlite3 status
python scripts/bounty_candidate_index.py --db scratch/global-discovery-audit-20261027/global-index.sqlite3 search
python scripts/bounty_candidate_index.py --db scratch/global-discovery-audit-20261027/global-index.sqlite3 step --steps 1 --limit 10 --max-pages 5
python scripts/bounty_candidate_index.py --db scratch/global-discovery-audit-20261027/global-index.sqlite3 retry --limit 10 --max-pages 5
python scripts/indexed_fleet_dispatcher.py --db scratch/global-discovery-audit-20261027/global-index.sqlite3
```

The index currently treats explicit dollar and USD-denominated stablecoin offers as candidates. Other currencies, uncertain payer authority, truncated pages, conflicting payment statements and unverified exchange rates remain deferred. GitHub search is not a snapshot: changing issue state and indexing lag require resweeps, and date partitioning alone cannot establish complete global coverage. A new creation-time range must be added with `extend`; periodic updated-issue searches are also needed to find older issues with newly added funding.

At the time of this audit, no active process matching `scripts/autonomous_icu_pipeline.py` was observed. That file contained separate uncommitted changes before this work; their diff was saved in the local audit directory. Small additional edits preserve the association of a verified funding commenter, include maintainer comments in the existing fetch, and prevent a missing ETH/USD quote from crashing the legacy search. The new index and handoff are local; automatic fleet dispatch has not been enabled or proven end to end with a live qualified candidate.

The added isolated index, handoff and scout tests, the existing discovery, scheduling, partition and ICU pipeline suites, Python compilation and Ruff checks for the new files passed. The existing live discovery test also passed and reported two raw candidates across its three queries; that test does not establish that they are funded and uncontested. The recovery and transport receipt suites passed; the latter emitted a Git line-ending warning in its temporary repository. A separate Ruff check of the legacy dispatcher found 29 existing findings: 28 are present at committed baseline `e786dde` and one is in the pre-existing uncommitted diff saved in the audit directory. Isolated tests exercise logic and do not substitute for live payment, availability or PR evidence.
