# _audit_missing.ps1 - existence audit of every file the kit references (read-only)
$root = 'D:\anonym\delivery\kilo-bridge-setup'
$refs = @(
  'scripts\_now.py','scripts\apply_answers.txt','scripts\prove_lane.py',
  'scripts\install-task.ps1','scripts\self-loop.ps1','scripts\lane_apply.py',
  'scripts\lane_jobs.py','scripts\lane_resume.py','scripts\agent360_client.py',
  'scripts\_wire_opencode.py','scripts\_semantic_diff.py','scripts\_probe_jobs_dom.py',
  'opencode.json.example','launch_profile17.py','prove_lane.py',
  'lane_foundit.py','lane_indeed.py','lane_linkedin.py','kilo_apply_resume.pdf',
  'docs\PACE.md','docs\FINAL-AGY-PROMPT-2026-09-24.md','docs\demo-video.mp4',
  'MISSION-RUN.txt','evidence\employment-lane\ledger.tsv',
  'war-log\launch_profile17.py','war-log\agent360_client.py','war-log\sweep-browser.token'
)
foreach ($r in $refs) {
  $inKit = Join-Path $root $r
  $inWar = Join-Path 'D:\anonym\war-log' $r
  $inAnon = Join-Path 'D:\anonym' $r
  $s1 = if (Test-Path $inKit) { 'KIT' } else { '---' }
  $s2 = if (Test-Path $inWar) { 'war-log' } else { '---' }
  $s3 = if (Test-Path $inAnon) { 'anonym' } else { '---' }
  Write-Host ("{0,-48} kit={1,-7} warlog={2,-7} anonym={3}" -f $r, $s1, $s2, $s3)
}