$ErrorActionPreference = 'Continue'
$pool = Get-Content 'D:\anonym\war-log\free_engine_pool_0913.json' -Raw | ConvertFrom-Json
function Try-Post($url, $key, $model, $label) {
  try {
    $body = @{ model = $model; max_tokens = 20; messages = @(@{ role = 'user'; content = 'reply PONG' }) } | ConvertTo-Json -Depth 4
    $t = Measure-Command { $r = Invoke-RestMethod $url -Method Post -Headers @{ Authorization = ('Bearer ' + $key) } -Body $body -ContentType 'application/json' -TimeoutSec 30 }
    $txt = ($r.choices[0].message.content) -join ''
    Write-Host ($label + ' OK ' + [int]$t.TotalMilliseconds + 'ms :: ' + $txt.Substring(0, [Math]::Min(80, $txt.Length)))
  } catch { Write-Host ($label + ' FAIL :: ' + $_.Exception.Message.Substring(0, [Math]::Min(160, $_.Exception.Message.Length))) }
}
Try-Post $pool.providers.tokenrouter.base $pool.providers.tokenrouter.keys[1] 'z-ai/glm-5.3-free' 'TOKENROUTER-glm5.3-free'
Try-Post $pool.providers.b_ai.base $pool.providers.b_ai.keys[1] 'qwen3.8-flash' 'B.AI-qwen3.8-flash'
Try-Post $pool.providers.b_ai.base $pool.providers.b_ai.keys[1] 'glm-5.3-flash' 'B.AI-glm5.3-flash'
try {
  $g = Get-Content 'C:\Users\Admin\.config\crush\crush.json' -Raw | ConvertFrom-Json
  $gk = $g.providers.groq.api_key
  Try-Post 'https://api.groq.com/openai/v1/chat/completions' $gk 'meta-llama/llama-4-scout-17b-16e-instruct' 'GROQ-llama4-scout'
} catch { Write-Host ('GROQ FAIL :: ' + $_.Exception.Message) }
