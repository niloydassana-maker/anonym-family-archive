$json = Get-Content 'D:\anonym\war-log\earn-lanes.json' -Raw | ConvertFrom-Json
$json.last_tick = '2026-09-20T15:50:12.184123+05:30'
$json.stale.feed_watch = '2026-09-20T15:50:12.184123+05:30'
$json.stale.weaver = 'DEAD'
$json.stale.awareness = '2026-09-20T15:50:12.236433+05:30'

$tickTime = '2026-09-20T15:50:12.184123+05:30'

$newActions = @(
    @{t=$tickTime; lane='L1'; action='Agent School DMs tick: drafts DM-22..DM-30 ready in OUT-0918/; zero sends without viewed-signal/Baba eye per verify law; broadcast already sent; LinkedIn notifications checked (no DM/enrollment signals); relay bank KILO logged'; evidence='war-log/roadmap/drafts/OUT-0918/agent-school-dm-pack.txt, adb dumpsys notification'; rs_pending='999-2999 x9 (DM-22..DM-30)'; rs_collected=0},
    @{t=$tickTime; lane='L2'; action='Service volley queue check: P-11..P-21 all AWAITING GO (standing GO for HIGH/MED fit); nudges HELD (P-2/P-3 no viewed-signal, Saikat demo-law); demos live (voice + dev)'; evidence='war-log/roadmap/drafts/OUT-0918/submit-queue-11.csv, nudge-ready.txt'; rs_pending='265000'; rs_collected=0},
    @{t=$tickTime; lane='L3'; action='Job-hunt NVite watch: no-new-data skip law honored; daily 3-5 applies target; Naukri mobile-only law maintained; ADB notifications checked (naukriApp, monsterindia, indeed - no NVite signals); NVite IDs captured as receipts'; evidence='war-log/evidence/L4/, adb dumpsys notification'; rs_pending='interview calls'; rs_collected=0},
    @{t=$tickTime; lane='L4'; action='Premium board expiry watch: cancel decision Sep 27 (T-7 days); mid-Oct window end; Rs 8k line held until L1 first Rs >= 1999; Talent Insights 404 retry via menu; Campaign PARKED'; evidence='todos.json id 49'; rs_pending='0'; rs_collected=0},
    @{t=$tickTime; lane='L5'; action='L5 Godshand/arbitrage PARKED - awaiting L1 first rupee'; evidence='earn-lanes.json l5.status'; rs_pending='0'; rs_collected=0},
    @{t=$tickTime; lane='INDUSIND'; action='Conciliation countdown: 21.09 3-4PM MS Teams from home -- T-1 DAY -- paper ready -- NEVER DEFER'; evidence='paper ready'; rs_pending='494899'; rs_collected=0}
)

foreach ($action in $newActions) {
    $json.action_log += $action
}

$json | ConvertTo-Json -Depth 10 | Set-Content 'D:\anonym\war-log\earn-lanes.json'