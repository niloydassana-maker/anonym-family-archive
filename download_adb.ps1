$url = 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip'
$out = $env:TEMP + '\platform-tools.zip'
(New-Object Net.WebClient).DownloadFile($url, $out)
Expand-Archive -Path $out -DestinationPath ($env:TEMP + '\platform-tools') -Force