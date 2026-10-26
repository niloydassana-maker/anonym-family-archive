# Fleet idle incident: 26 October 2026

## Finding and outcome

The dispatcher delivery database had a corrupt primary-key index. The real
`deliveries` table contained **196 rows**, while its primary-key index contained
**212 entries**. Six of the resulting 16 ghost keys appeared in the current
discovery sample. Looking up those keys returned unrelated stored failure states,
so the dispatcher skipped issues that had no real delivery row.

The five Kaggle workers were running and repeatedly polling successfully. They
had no new runnable work because the dispatcher was not adding tasks. Restarting
the fleet alone did not repair the dispatcher database.

After preserving the database, rebuilding the index, and restarting the
dispatcher with the supported `--live --anytime` arguments, its normal search
cycle dispatched new tasks. Engine 5 then claimed and started the Cline workflow
for **paraloom-labs/paraloom-core#992**. Engine 2 also claimed core#988. Their
heartbeats subsequently reported `phase=CARGO_CHECK_WORKSPACE`: native baseline
verification was active. This establishes recovery through dispatch, claim, and
workflow execution; it does not establish completed implementations or PRs.

All times below are Asia/Kolkata, unless explicitly marked UTC.

## Authentic timeline

| Time | Evidence |
| --- | --- |
| 18:01:29 | Last new queue record before the incident repair: BasedHardware/omi#23720. |
| 19:09:31 | Last claim before the repair: ClawPowers-Skills#126, attempt 4. |
| 19:20:50 | That existing task reported success and PR #208. Thus there was a completion during the requested three-hour window, but no fresh dispatch. |
| 19:53:32 | Last fleet startup registration in the original ledger snapshot. |
| 20:49:57 | The earlier dispatcher stdout file had been reduced to zero bytes. Its former contents were unavailable for this RCA. |
| 21:08:40 | A dispatcher process was started with `--live --all-lanes`. The implementation does not recognize `--all-lanes`. |
| 21:40 onward | Read-only RCA began; all five Kaggle kernels reported RUNNING. Their live logs repeatedly showed `POLL_OK HTTP 200 tasks=6 prior_poll_failures=0`. |
| 21:51:59 | Full database integrity inspection and preservation captured the corrupt index and 16 ghost keys. |
| 21:53:04 | Live index repair completed, with all 196 table rows unchanged and `PRAGMA integrity_check = ok`. |
| 21:53:35 | Dispatcher restarted as PID 18140, with `--live --anytime` and dedicated stdout/stderr files. |
| 21:56:09 | Queue event 126: the normal dispatcher rediscovered and dispatched core#992. |
| 21:56:19 | Queue event 127: core#1004 was dispatched; subsequent cross-repository competition review excluded this mirrored wallet task. |
| 21:56:32 | Queue event 128: the dispatcher dispatched core#988. |
| 21:57:07 | Claim event 130: Engine 5 claimed core#992, attempt 1. |
| 21:57:08 | Execution event 131: Engine 5 started the Cline workflow for core#992. |
| 21:57:36 | Claim event 132: Engine 2 claimed core#988; execution event 133 followed. |
| 21:59:24 | Queue event 137: the dispatcher dispatched Go-Hybrid#186. |
| 21:59:48 | Engine 3 claimed Go-Hybrid#186. It then stopped at the existing `FAILED_NO_TEST_VERIFICATION` gate because no native test commands were discovered. This is a separate verification-discovery limitation, not continued queue starvation. |

The historical three-hour gate counts cannot be reconstructed exactly from the
erased dispatcher log. The discovery counts below are an authentic live replay
of the current source, not manufactured historical measurements.

## Confirmed causal failure

The primary key is `(repo, issue_number)`. Dispatch begins by calling
`is_issue_claimed_or_delivered`, which queries that key. Any existing state other
than an eligible `RETRY_PENDING` state blocks the candidate.

Before repair, the following real reads disagreed:

```text
PRAGMA quick_check
  ok

PRAGMA integrity_check
  wrong # of entries in index sqlite_autoindex_deliveries_1

SELECT count(*) FROM deliveries NOT INDEXED
  196

SELECT count(*) FROM deliveries INDEXED BY sqlite_autoindex_deliveries_1
  212
```

`quick_check` alone therefore missed this defect. The full integrity check exposed
the mismatch between the table and its index.

A concrete example was core#992. An indexed lookup returned
`FAILED_EXHAUSTED`, with reason `Dispatcher reset: stale dispatch from earlier
cycle`, while a forced table scan found **no row for that issue**. After rebuilding
the index, the lookup correctly found no row, and the normal dispatcher accepted
the issue without any policy bypass.

The six ghost keys encountered in the discovery replay were:

- paraloom-labs/paraloom-core#988, #992, #1004, and #1138;
- paraloom-labs/paraloom-wallet#93;
- limitlessprojects/Go-Hybrid#186.

The index also contained ten other ghost keys, preserved in
`scratch/rca-no-tasks-20261026/database-before-repair.json`.

**The operation and exact time that originally corrupted the index are not
established.** There is no evidence sufficient to attribute it to a particular
agent, test, restore, or file write. The diagnosis is based on the corrupt state,
its demonstrated effect on issue lookups, and task flow resuming after repair.

## Discovery replay and contributing factors

The RCA replayed all 23 current queries through the actual search implementation,
recording GitHub responses and the exact filter lines taken. It then checked
remaining candidates against current issue data, author territory, ledger state,
and open PRs. No model was used to fabricate candidates or measurements.

| Stage, before index repair | Count |
| --- | ---: |
| GitHub result occurrences across 23 searches | 645 |
| Distinct issues returned | 442 |
| Distinct issues surviving the search filter | 49 |
| Reported blocked by the delivery ledger | 19 |
| Not blocked by that ledger lookup | 30 |
| Of those 30, rejected by the live eligibility gate | 26 |
| Preliminary survivors requiring final review | 4 |
| Of those four, bot-authored submissions | 2 |
| Other two, excluded territory and existing competing PRs | 2 |

Six of the 19 ledger blocks were caused by ghost index keys. Thus this funnel
would falsely look like a complete absence of eligible work unless the database
was independently checked.

Other operational findings:

1. **Unsupported launch argument.** `main()` enables unrestricted scheduling only
   for `--anytime` or `--24x7`. It silently ignored the observed `--all-lanes`
   argument. That allowed business-hours holds to apply. This was corrected in
   the restart. It is an additional defect, not proof that the four final
   candidates above were held for business hours.
2. **Search depth and filtering.** The current cycle requests 30 newest results
   per query and requires at most two comments. Filtering happens after retrieval
   and does not refill the page. The banner still advertises 1,000 results.
   Checkpoint a376f67 also called `search_issues(..., limit=30)`, so the 30-result
   call alone is not a demonstrated regression from that checkpoint.
3. **Historical terminal states.** Genuine table rows still include verification
   failures classified as `REJECTED_SECURITY`, and resets classified as
   `FAILED_EXHAUSTED`. These require case-specific review. They were not globally
   cleared during this repair.
4. **Incomplete operational evidence.** Kernel RUNNING and startup ONLINE
   receipts established liveness, but did not establish advancing dispatch or
   execution. The earlier health report missed the corrupt dispatcher index.
   Lost dispatcher logs further limited retrospective reconstruction.
5. **Cross-repository competition.** core#1004 describes the same wallet work as
   wallet#93, already covered by wallet PR #100. The current per-repository PR
   check did not catch that relationship. Controller result event 129 explicitly
   skipped core#1004 before a worker claim appeared in the recorded ledger.

The two legacy 20,000-character malformed records remain preserved in the old
queue. Workers reject those records and continue polling. They did not prevent
the new core#992 task from being claimed after this repair.

## Repair and verification

1. Preserved a SQLite backup of the corrupt database and the indexed/table views.
2. Rebuilt the index on a separate copy first. Verified full integrity, equal
   table/index counts, and exact preservation of every real delivery row.
3. Stopped the identified dispatcher process chain, preserving its launch details.
4. Took a second backup and ran `REINDEX sqlite_autoindex_deliveries_1` inside an
   immediate transaction on the live database.
5. Required `PRAGMA integrity_check = ok`, equal counts of 196, and exact equality
   of all table rows before committing.
6. Restarted the existing dispatcher source with `--live --anytime`, a single
   process, and durable log paths.
7. Observed the normal dispatcher independently produce new queue events. A
   separately prepared check of core#992 stopped because the dispatcher had
   already reserved it; it did not enqueue a duplicate.
8. Observed Engine 5 claim and start core#992 through the real fleet ledger.

This was an operational database repair and process restart. No production
Python implementation, eligibility rule, or existing test was changed. The
verification directly exercised the preserved corrupt database, the repaired
live database, and the real dispatch/claim/execution path.

## Evidence and prevention

Evidence directory: `scratch/rca-no-tasks-20261026/`.

| Artifact | Purpose |
| --- | --- |
| `database-before-repair.json` | Full integrity failure, 16 ghost keys, real table rows. |
| `icu_pipeline-corrupt-preserved.sqlite3` | First preserved corrupt database. SHA-256: `1e422aa4c94b5fa7a4f91557a2878544ea14c55af2a56c3685168ff50ad472d3`. |
| `icu_pipeline-before-live-reindex.sqlite3` | Backup taken immediately before live repair. SHA-256: `0ea8449d90557bc4148e1384d82d384353d7a58babbe3bc9ff771db62897836c`. |
| `database-repair-receipt.json` | Successful integrity check and unchanged table-row receipt. |
| `live-search-funnel.json` | Authentic GitHub responses and actual filter decisions for all 23 queries. |
| `locked-candidates.json` | Fresh issue, funding, territory, and competition checks. |
| `engine-1-logs.json` through `engine-5-logs.json` | Live Kaggle polling receipts. Log collection ended after a bounded quiet-stream read timeout; that timeout was in the diagnostic reader, not the workers. |
| `dispatcher-restart-receipt.json` | Corrected launch arguments and process ID. |
| `dispatcher-after-repair.stdout.log` | New normal-cycle dispatch confirmations. |
| `cross-repository-competition-skip.json` | Explicit exclusion of the mirrored wallet task. |
| `live-recovery-receipt.json` | Post-repair integrity check, new queue entries, actual claims, baseline heartbeats, and the separate Go-Hybrid test-discovery failure. |
| `evidence-sha256.json` | SHA-256 hashes of preserved JSON evidence and database copies. |

Recommended follow-up controls, not claimed as implemented in this RCA:

- Run the full SQLite integrity check before dispatch starts and after a restore;
  require a clean result before trusting indexed delivery lookups.
- Use SQLite backup operations and a controlled writer shutdown for database
  restore or replacement; do not treat a raw live-file copy as a safe restore.
- Reject unsupported CLI arguments and record the effective scheduling mode.
- Retain timestamped dispatcher logs and measure last new dispatch, worker claim,
  execution, and verified PR separately from process liveness.
- Review historical failure states individually against authentic receipts.
- Extend competition review to issue mirrors that identify another repository as
  the actual implementation target.
