$client = New-Object System.Net.WebClient
try {
    $result = $client.DownloadString("http://127.0.0.1:8777/say?token=GOLD24&body=KILO%20KDP-SESSION-ABSENT")
    "Success: " + $result
} catch {
    "Error: " + $_.Exception.Message
}