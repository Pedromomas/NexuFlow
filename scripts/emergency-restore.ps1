$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

$EngineCandidates = @(
  ".\src-tauri\binaries\nexus-engine-x86_64-pc-windows-msvc.exe",
  ".\engine\dist\nexus-engine.exe"
)
$Engine = $EngineCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Engine) {
  throw "NexuFlow engine não encontrado. Rode .\scripts\build-engine.ps1 primeiro."
}

$Token = [guid]::NewGuid().ToString()
$Jobs = Join-Path $env:TEMP "NexuFlow\jobs"
New-Item -ItemType Directory -Force $Jobs | Out-Null
$Request = Join-Path $Jobs "$Token.request.json"
$Result = Join-Path $Jobs "$Token.result.json"

$Payload = @{
  schema = 1
  action = "restore"
  profile = "safe"
  requested_by = "tauri"
} | ConvertTo-Json
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Request, $Payload, $Utf8NoBom)

& $Engine --request $Request --result $Result

$Deadline = (Get-Date).AddSeconds(30)
while (-not (Test-Path $Result) -and (Get-Date) -lt $Deadline) {
  Start-Sleep -Milliseconds 200
}

if (-not (Test-Path $Result)) {
  throw "O helper elevado não retornou resultado. Verifique se o UAC foi cancelado."
}

Get-Content $Result -Raw | Write-Host
Remove-Item $Request, $Result -Force -ErrorAction SilentlyContinue
