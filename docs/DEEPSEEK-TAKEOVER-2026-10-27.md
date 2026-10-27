# DeepSeek takeover prompt

Paste the following into the selected DeepSeek session in OpenCode:

---

Baba has authorized you to take over the bounty pipeline at `D:\anonym`. Read `AGENTS.md`, then these documents before acting:

1. `docs/ACTIONS-REPAIR-VERIFICATION-2026-10-27.md`
2. `docs/ACTIONS-THREE-LAYER-E2E-AUDIT-2026-10-27.md`
3. `docs/ACTIONS-MIGRATION-REPAIR-PATH-2026-10-27.md`
4. `docs/ACTIONS-REPAIR-RECEIPTS-2026-10-27.json`

Current tested code: `5c4811cf2b1b5b5aef34d6c7a1ab255392551e1c`. The final Linux contract run `40531287767` passed all 32 new cases plus unchanged suites. Active discovery at handoff: `40531780003`; inspect its result before launching another cycle.

Start with `git status --short` and `git log -8 --oneline`. Work on the current master of `isearchxsolve/anonym-family-archive`; do not reset or clean this shared laptop workspace. There are unrelated untracked debug scripts, a `deliverables/toneart-demo/` directory, and a modified `temp_status.json`. Preserve them. Stage explicit task files only. Never push vaults, private family documents or credentials.

The infrastructure repair is deployed, but the BUSINESS GOAL IS STILL OPEN: **high qualified influx + high quality + genuinely hard issues + live end-to-end receipts together**. Do not call a green canary, raw search count, accepted dispatch or mocked unit test a completed bounty delivery. The last two complete discovery receipts had zero qualified dispatches. Continue the iteration honestly from that point.

Kaggle is banned. Compute runs on GitHub Actions. The laptop is for lightweight control, audit and contract tests. The cloud dispatcher has normal, startup and founder lanes under one shared policy. Do not revive old Kaggle dispatchers or start competing local daemons.

The code is in:

- `.github/workflows/engine2.yml`: claim → engineer → publish → reconcile; manual `mode=canary` performs a real model/tool handshake.
- `.github/workflows/bounty-discovery.yml`: recurring global search and result reconciliation, with persistent cache and artifacts.
- `.github/workflows/actions-contracts.yml`: unchanged master suites plus Actions regression contracts.
- `scripts/actions_dispatch.py`, `bounty_queries.json`, `discovery_horizon.py`: global fresh/backlog queries, pagination, durable pending sources, queued candidates and policy-cache invalidation.
- `scripts/bounty_admission.py`, `bounty_fx.py`: shared issuer/amount/source/hard-scope policy and observed currency quotes. The configured floor is USD 80. Do not manufacture amounts from severity.
- `scripts/actions_github.py`: full context, independent visible-comment count confirmation, canonical task ID and durable control-branch state.
- `scripts/actions_delivery.py`, `actions_release.py`, `actions_reconcile.py`: Cline-first lifecycle, independent native/regression verification, preserved checkpoints, isolated publication and PR/check follow-through.
- `scripts/kaggle_engine_worker.py`, `delivery_supervisor.py`: reused lifecycle library, despite the historical filename. Do not invoke the Kaggle bootstrap/main.

Cline is the first PROJECT EXECUTOR after claim. It owns repository-specific package-manager choice, pins, installations, configuration, test-plan discovery, implementation and repair. No host npm/pnpm/test-plan failure may reject the project before Cline intake. Keep the correct agent package `cline@3.0.74` and the native-tool-preserving gateway; do not revert to `@cline/cli`/`clite` or a text-flattening proxy. Node 22 is bootstrapped for the agent. Every Cline turn has 3,600 seconds. Preserve completed edits and use the retained artifact/checkpoint on recovery; do not regenerate from an empty checkout unnecessarily.

Keep the independent release requirements: clean upstream baseline, actual component exists, genuine product change, full native builds/tests/linters with no warnings, untouched master tests, new companion regression red on upstream source and green on the fix, one verified task commit, current funding and zero open competing PRs. No unverified PRs. Updating an owned PR requires exact-head ownership and `--force-with-lease`; never blanket-force. Pending CI or maintainer approval is a waiting state, not a reason to regenerate verified code.

The provider keys and publisher token are already GitHub Actions secrets (`TOKENHARBOR_KEYS_JSON`, `GH_PAT`). Do not retrieve or print their values. The engineer job has no publisher PAT; publication is a separate trusted job. Ordinary environment cleanup is not a hostile-code sandbox, so do not claim perfect secret isolation under unrestricted provisioning.

Proven receipts:

- Live canary: `40530525138` on gateway/delivery code `5bc9023`; HTTP 200, two completed model requests and one returned tool result. Earlier canary `40528748332` also passed.
- Linux contracts: `40530523348` passed 31 new cases plus unchanged suites. Final run `40531287767` passed all 32 cases, including subsequent cache/approval tests, plus unchanged suites.
- Discovery `40528756264` persisted 605 unique sources, checked 60 and retained 545. Discovery `40529552133` restored that cache and retained 525 after the next batch. Both had zero qualified dispatches. Policy changes now requeue stale rejections, so a new-policy run may correctly revisit earlier sources.
- Local raw evidence: `scratch/actions-repair-20261027/`. Original audit evidence: `scratch/actions-e2e-audit-20261027/`. Source fixes and evidence boundaries are in the verification document.

Immediate next actions:

```powershell
gh run list --repo isearchxsolve/anonym-family-archive --limit 10 --json databaseId,name,status,conclusion,headSha,url
gh workflow run bounty-discovery.yml --repo isearchxsolve/anonym-family-archive --ref master
```

Do not duplicate an already running discovery job; check first. Download the latest discovery artifact with `gh run download RUN_ID --repo isearchxsolve/anonym-family-archive --dir scratch/CHOOSE_A_NEW_DIRECTORY`, inspect `receipts.jsonl`, cursors, pending rows and exact rejection evidence. Queries are global; keep all original repository/owner possibilities in scope. Resolve mirrors back to the original issue. Recheck old false negatives after a policy fix. GitHub search cannot itself prove current payment authority, native verification or absence of a last-minute PR; preserve those factual checks rather than pretending GitHub supports custom executable predicates.

Audit candidate rejection reasons against live source, not guessed counts. Two false-negative defects were repaired: repeated money matches after code-block removal used incorrect offsets; REST issue comment counters differed from the independently visible GraphQL connection. Do not loosen source completeness or funding authority without actual API evidence. Genuine SpaceApp $400/$750/$600 offers were found but had competing PRs; do not claim them as eligible influx.

When a genuine candidate clears the shared policy, use the dispatcher, or a reviewed direct delivery launch with:

```powershell
gh workflow run engine2.yml --repo isearchxsolve/anonym-family-archive --ref master -f mode=deliver -f target_repo=ORIGINAL_OWNER/ORIGINAL_REPO -f issue_number=ACTUAL_ISSUE_NUMBER
```

Those uppercase values are placeholders, not commands to execute unchanged. Observe the real claim, Cline intake, baseline, native verification, regression proof, release artifacts, PR head and remote checks. Record real blocked reasons and preserve edits. Inspect publisher/reconciler behavior on a genuine task; it has contract coverage but no completed bounty delivery receipt yet. Measure qualified throughput and verified deliveries across cycles, not just one raw-results counter.

Run the unchanged local suites and `scripts/test_actions_migration.py` with `python -W error` for relevant code changes. Existing master tests must remain unchanged. Check Ruff and workflow syntax. Commit/push only tested repair files, attach exact run URLs and SHA-256 receipts, and update the verification document with what was actually observed. Do not claim the combined goal achieved until real funded hard issues pass the full path and qualified influx is sustained.

Report to Baba warmly and briefly: what is proven, what remains, and the next actual receipt. No false DONE.

---
