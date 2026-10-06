$ErrorActionPreference = 'Continue'
$pool = Get-Content 'D:\anonym\war-log\free_engine_pool_0913.json' -Raw | ConvertFrom-Json
$nvk = $pool.providers.nvidia.keys[10]
Write-Host '--- NVIDIA direct: llama-3.1-nemotron-ultra-253b-v1 ---'
try {
  $body = @{ model = 'nvidia/llama-3.1-nemotron-ultra-253b-v1'; max_tokens = 20; messages = @(@{ role = 'user'; content = 'reply PONG' }) } | ConvertTo-Json -Depth 4
  $t = Measure-Command { $r = Invoke-RestMethod $pool.providers.nvidia.base -Method Post -Headers @{ Authorization = ('Bearer ' + $nvk) } -Body $body -ContentType 'application/json' -TimeoutSec 60 }
  Write-Host ('OK ' + [int]$t.TotalMilliseconds + 'ms :: ' + ($r.choices[0].message.content -join ''))
} catch { Write-Host ('FAIL :: ' + $_.Exception.Message.Substring(0, 200)) }
Write-Host '--- NVIDIA direct: nemotron-3-super-120b ---'
try {
  $body = @{ model = 'nvidia/nemotron-3-super-120b-a12b'; max_tokens = 20; messages = @(@{ role = 'user'; content = 'reply PONG' }) } | ConvertTo-Json -Depth 4
  $t = Measure-Command { $r = Invoke-RestMethod $pool.providers.nvidia.base -Method Post -Headers @{ Authorization = ('Bearer ' + $nvk) } -Body $body -ContentType 'application/json' -TimeoutSec 60 }
  Write-Host ('OK ' + [int]$t.TotalMilliseconds + 'ms :: ' + ($r.choices[0].message.content -join ''))
} catch { Write-Host ('FAIL :: ' + $_.Exception.Message.Substring(0, 200)) }
Write-Host '--- GROQ gpt-oss-120b ---'
try {
  $g = Get-Content 'C:\Users\Admin\.config\crush\crush.json' -Raw | ConvertFrom-Json
  $gk = $g.providers.groq.api_key
  $body = @{ model = 'openai/gpt-oss-120b'; max_tokens = 20; messages = @(@{ role = 'user'; content = 'reply PONG' }) } | ConvertTo-Json -Depth 4
  $t = Measure-Command { $r = Invoke-RestMethod 'https://api.groq.com/openai/v1/chat/completions' -Method Post -Headers @{ Authorization = ('Bearer ' + $gk) } -Body $body -ContentType 'application/json' -TimeoutSec 60 }
  Write-Host ('OK ' + [int]$t.TotalMilliseconds + 'ms :: ' + ($r.choices[0].message.content -join ''))
} catch { Write-Host ('FAIL :: ' + $_.Exception.Message.Substring(0, 200)) }
