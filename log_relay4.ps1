$client = New-Object System.Net.WebClient
$client.Headers.Add("Content-Type", "application/x-www-form-urlencoded")
try {
    $result = $client.UploadString("http://127.0.0.1:8777/say?token=GOLD24", "body=KILO KDP-SESSION-ABSENT")
    "Success: " + $result
} catch {
    "Error: " + $_.Exception.Message
}