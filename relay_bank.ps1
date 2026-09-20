try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8777/say?token=GOLD24' -Method POST -Body 'KILO' -TimeoutSec 5
    Write-Host "STATUS: $($r.StatusCode)"
    Write-Host 'RELAY_BANK_OK'
} catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
    }
    Write-Host "STATUS: $statusCode"
    Write-Host "ERROR: $($_.Exception.Message)"
    if ($statusCode -eq 429 -or $statusCode -eq 503) {
        Write-Host 'EXIT_QUIETLY_429_503'
        exit 0
    }
}