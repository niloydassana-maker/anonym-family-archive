# Video deliverable search exclusion — 2026-10-28

## Live false-positive and Cline receipt

Discovery run [`40606253662`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40606253662)
ran on `1cafe162e31ed98ccc25f579aca988e652b692cb` and found one qualified candidate,
`bolivian-peru/os-moda#3`. The live offer was 1 SOL, but its deliverable was a filmed video,
not a code change.

Delivery run [`40606461264`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40606461264)
launched Cline as the first engineering actor. Cline read the full issue and repository, then
recorded `REJECTED_PREPARATION` with the checkout unchanged. The issue is labeled `video-demo`,
requires two real servers and a camera, and demands a public YouTube upload. The maintainer's
comment [3981669467](https://github.com/bolivian-peru/os-moda/issues/3#issuecomment-3981669467)
states: “This is not a code bounty. There is no bug to fix. There is no PR to submit. This is a
video production bounty.” The task was therefore not a valid code-delivery candidate.

The workflow and Cline completed successfully, but this was a correct refusal, not a PR or an
extended-timeout test: Cline ran for about 80 seconds. The four-hour budget is configured in
the deployed workflow; a delivery taking over an hour is still needed to prove its long-run
behavior.

## Repair

- Added `-label:video-demo` to the common GitHub issue-search qualifiers. It is applied to every
  lane, priority-program query, and expanded OR branch before results are returned.
- Bumped the query policy version so the durable cache is revisited.
- During cache migration, retire stale rows with `video-demo`, `type/experiment`, or assignees
  under the same query-excluded status contract. This prevents old cached hits from bypassing
  the new server-side filter.
- Added regression coverage for query expansion and stale-cache retirement. Funding, code-scope,
  competition, and native-verification requirements remain intact.

## Verification status

Live discovery run [`40607203671`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40607203671)
completed successfully on commit `c1805df7b885b9b6cfb7b6f5de30d8ae6a927902`:

- Search-policy migration logged `-label:video-demo`, retired 3 stale video-demo cache rows,
  and retired 967 assigned rows.
- All 9 emitted lane/branch search records contained `-label:video-demo`; none contained
  `bolivian-peru/os-moda#3` in admission.
- A direct live GitHub search found three open issues with the `video-demo` label in that
  repository when unfiltered; the equivalent query with `-label:video-demo` returned no rows.
- Raw lane counts were programs 38, normal 473, startup 37, founder 15. These are raw search
  results and overlap across lanes; they are not unique qualified tasks.
- Final admission was `qualified_fresh=0`, `qualified_unique=0`, `dispatched=[]`, with 7,049
  pending hydration rows. The query repair is proven, but qualified influx remains unproven.

A zero in the `video-demo` sample is only an exclusion receipt; it does not count as qualified
influx. A valid influx receipt still requires funded hard engineering tasks, and delivery
success still requires a real verified pull request. Run the next fresh cursor windows to
continue measuring qualified unique tasks without weakening any admission or release gate.
