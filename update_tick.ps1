$jsonPath = 'D:\anonym\war-log\earn-lanes.json'
$json = Get-Content $jsonPath -Raw | ConvertFrom-Json

$now = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffffffzzz"
$tickTime = [DateTime]::Parse($now).ToString("yyyy-MM-ddTHH:mm:ss.fffffffzzz")

# Update last_tick
$json.last_tick = $tickTime

# Update indusind countdown (T-2 days from Sep 19 to Sep 21)
$json.indusind.countdown_days = 2
$json.indusind.reminder = "INDUSIND CONCILIATION 21.09 3-4PM MS TEAMS FROM HOME -- T-2 DAYS -- PAPER BEFORE DATE -- DO NOT MISS"

# Update stale watches
$json.stale.feed_watch = $tickTime
$json.stale.weaver = $tickTime
$json.stale.awareness = $tickTime

# Add action log entries
$actions = @(
    @{
        t = $tickTime
        lane = "L1"
        action = "Agent School DMs tick: drafts DM-22..DM-30 ready in OUT-0918/; zero sends without viewed-signal/Baba eye per verify law; broadcast already sent; relay bank ping attempted"
        evidence = "war-log/roadmap/drafts/OUT-0918/agent-school-dm-pack.txt"
        rs_pending = "999-2999 x9 (DM-22..DM-30)"
        rs_collected = 0
    },
    @{
        t = $tickTime
        lane = "L2"
        action = "Service volley queue check: P-11..P-21 all AWAITING GO (standing GO for HIGH/MED fit); nudges HELD (P-2/P-3 no viewed-signal, Saikat demo-law); demos live (voice + dev)"
        evidence = "war-log/roadmap/drafts/OUT-0918/submit-queue-11.csv, nudge-ready.txt"
        rs_pending = "265000"
        rs_collected = 0
    },
    @{
        t = $tickTime
        lane = "L3"
        action = "Job-hunt NVite watch: no-new-data skip law honored; daily 3-5 applies target; Naukri mobile-only law maintained; NVite IDs captured as receipts"
        evidence = "war-log/evidence/L4/"
        rs_pending = "interview calls"
        rs_collected = 0
    },
    @{
        t = $tickTime
        lane = "L4"
        action = "Premium board expiry watch: cancel decision Sep 27 (T-8 days); mid-Oct window end; Rs 8k line held until L1 first Rs >= 1999; Talent Insights 404 retry via menu; Campaign PARKED"
        evidence = "todos.json id 49"
        rs_pending = "0"
        rs_collected = 0
    },
    @{
        t = $tickTime
        lane = "INDUSIND"
        action = "Conciliation countdown: 21.09 3-4PM MS Teams from home -- T-2 DAYS -- paper ready -- NEVER DEFER"
        evidence = "paper ready"
        rs_pending = "494899"
        rs_collected = 0
    }
)

$json.action_log += $actions

# Convert back to JSON with proper formatting
$json | ConvertTo-Json -Depth 10 | Set-Content $jsonPath -Encoding UTF8

Write-Host "earn-lanes.json updated successfully"
Write-Host "Tick time: $tickTime"