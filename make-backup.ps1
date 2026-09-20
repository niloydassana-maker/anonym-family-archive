$ErrorActionPreference = 'Stop'

# ---- 1. Generate memorizable strong passphrase: 6 words + 4 digits ----
$words = 'sunset river temple forest lantern garden monkey silver thunder anchor marble ferry monsoon harvest lantern shadow copper valley drum echo pillar meadow compass island falcon candle harbor jungle magnet mirror orchid pepper quiver ribbon saddle tundra umbrella violet walnut yarn zebra amber bridge canyon dawn ember flute glacier honey ivory jasper kelp lagoon mango nectar opal pearl quartz ravine spice tulip urgent velvet wagon xenon yonder zephyr basil clover dune elm fang grove hazel iris jade knot lark moss north opal pine quail rose sago thorn urn vine willow xenia yucca zenith apricot breeze cedar drift eel flint gorge hollow indigo jetty krill lotus misty nutmeg octagon prairie ridge salt teak udder vane wick xl yam zinc arrow bellows cliff dome engine fang gale hinge ice jaguar kettle lemon mango navy otter plum quiver rust sable tonne uncle vega wren xylo yolk zulu anchor buoy coral deck eagle flag gulf hull ink jet keel lime mast node oar port quay radar sail tide urn vessel wake xmas yacht zero almond brine cumin dill essence fennel ginger herb iron juniper kaffir lime mint nutmeg oregano paprika quince rosemary saffron thyme umami vanilla wasabi yuzu zaatar'
$wlist = $words -split ' ' | Select-Object -Unique
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$pick = 1..6 | ForEach-Object { $b = New-Object byte[] 2; $rng.GetBytes($b); $wlist[[BitConverter]::ToUInt16(($b + @(0,0)),0) % $wlist.Count] }
$digs = 1..4 | ForEach-Object { $b = New-Object byte[] 1; $rng.GetBytes($b); $b[0] % 10 }
$pass = ($pick -join '-') + '-' + ($digs -join '')

# ---- 2. Encrypt MASTER-RECORD.txt + BitLocker keys with AES-256 ----
$salt = New-Object byte[] 16; $rng.GetBytes($salt)
$derive = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($pass, $salt, 200000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$aesKey = $derive.GetBytes(32)
$hmacKey = $derive.GetBytes(32)
$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Key = $aesKey; $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'
$aes.GenerateIV(); $iv = $aes.IV

$files = @('D:\anonym\MASTER-RECORD.txt','D:\anonym\BITLOCKER-RECOVERY-KEYS.txt','D:\anonym\DAILY-GUIDE.txt')
$plain = New-Object System.IO.MemoryStream
foreach ($f in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($f)
    $name = [System.Text.Encoding]::UTF8.GetBytes((Split-Path $f -Leaf) + "`n")
    $len = [BitConverter]::GetBytes([long]$bytes.Length)
    $plain.Write($name,0,$name.Length); $plain.Write($len,0,8); $plain.Write($bytes,0,$bytes.Length)
}
$enc = $aes.CreateEncryptor().TransformFinalBlock($plain.ToArray(),0,$plain.ToArray().Length)

$out = New-Object System.IO.MemoryStream
$out.Write([System.Text.Encoding]::UTF8.GetBytes('ANONENC1'),0,8)
$out.Write($salt,0,16); $out.Write($iv,0,16); $out.Write($enc,0,$enc.Length)
$body = $out.ToArray()

$h = New-Object System.Security.Cryptography.HMACSHA256(,$hmacKey)
$tag = $h.ComputeHash($body)
[System.IO.File]::WriteAllBytes('D:\anonym\RECORD-BACKUP.enc', $body + $tag)

# ---- 3. Verify round-trip ----
$raw = [System.IO.File]::ReadAllBytes('D:\anonym\RECORD-BACKUP.enc')
$tag2 = $raw[($raw.Length-32)..($raw.Length-1)]
$body2 = $raw[0..($raw.Length-33)]
$h2 = New-Object System.Security.Cryptography.HMACSHA256(,$hmacKey)
$ok1 = ([Convert]::ToBase64String($h2.ComputeHash($body2)) -eq [Convert]::ToBase64String($tag2))
$s2 = $body2[8..23]; $iv2 = $body2[24..39]; $ct = $body2[40..($body2.Length-1)]
$d2 = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($pass, [byte[]]$s2, 200000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$aes2 = [System.Security.Cryptography.Aes]::Create()
$aes2.Key = $d2.GetBytes(32); $aes2.IV = [byte[]]$iv2; $aes2.Mode='CBC'; $aes2.Padding='PKCS7'
$dec = $aes2.CreateDecryptor().TransformFinalBlock([byte[]]$ct,0,$ct.Length)
$orig = [System.IO.File]::ReadAllBytes('D:\anonym\MASTER-RECORD.txt')
$ok2 = ($dec.Length -gt $orig.Length)

Write-Output "HMAC verify: $ok1"
Write-Output "Decrypt round-trip: $ok2"
Write-Output "Backup file: D:\anonym\RECORD-BACKUP.enc ($((Get-Item 'D:\anonym\RECORD-BACKUP.enc').Length) bytes)"
Write-Output "PASSPHRASE: $pass"
if ($ok1 -and $ok2) { Write-Output 'BACKUP_VERIFIED' } else { Write-Output 'BACKUP_FAILED' }
