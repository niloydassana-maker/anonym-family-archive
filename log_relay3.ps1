$r = Invoke-WebRequest -Uri 'http://127.0.0.1:8777/say?token=GOLD24&body=KILO%20KDP-SESSION-ABSENT' -Method Get
$r.StatusCode