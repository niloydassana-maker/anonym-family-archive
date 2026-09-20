param(
    [string]$Passphrase = '',
    [string]$OutDir = "D:\anonym\restored-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)
$ErrorActionPreference = 'Stop'

if ($Passphrase -eq '') {
    $ss = Read-Host 'Passphrase' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)
    $Passphrase = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}

$raw = [System.IO.File]::ReadAllBytes('D:\anonym\RECORD-BACKUP.enc')
$tag = $raw[($raw.Length-32)..($raw.Length-1)]
$body = $raw[0..($raw.Length-33)]
$salt = [byte[]]$body[8..23]
$iv = [byte[]]$body[24..39]
$ct = [byte[]]$body[40..($body.Length-1)]

$derive = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Passphrase, $salt, 200000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$aesKey = $derive.GetBytes(32)
$hmacKey = $derive.GetBytes(32)

$h = New-Object System.Security.Cryptography.HMACSHA256(,$hmacKey)
$ok = ([Convert]::ToBase64String($h.ComputeHash($body)) -eq [Convert]::ToBase64String($tag))
if (-not $ok) {
    Write-Output 'RESTORE_FAILED: wrong passphrase or file tampered'
    exit 1
}

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Key = $aesKey; $aes.IV = $iv; $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'
$dec = $aes.CreateDecryptor().TransformFinalBlock($ct, 0, $ct.Length)

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$pos = 0
while ($pos -lt $dec.Length) {
    $nl = [Array]::IndexOf($dec, [byte]10, $pos)
    $name = [System.Text.Encoding]::UTF8.GetString($dec, $pos, $nl - $pos)
    $len = [BitConverter]::ToInt64($dec, $nl + 1)
    $start = $nl + 9
    [System.IO.File]::WriteAllBytes((Join-Path $OutDir $name), [byte[]]$dec[$start..($start+$len-1)])
    Write-Output "restored: $name"
    $pos = $start + $len
}
Write-Output "RESTORE_OK -> $OutDir"
