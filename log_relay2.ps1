$r = Invoke-WebRequest -Uri 'http://127.0.0.1:8777/say?token=GOLD24' -Method Post -Body 'body=KILO KDP-SESSION-ABSENT' -ContentType 'application/x-www-form-urlencoded'
$r.StatusCode