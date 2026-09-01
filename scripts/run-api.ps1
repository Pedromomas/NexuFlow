param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."

# Somente o terminal da API local é elevado. A UI Ionic/Tauri continua normal.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
  # Prefer PowerShell 7 when installed, but keep compatibility with Windows
  # PowerShell 5.1. Both start the same loopback-only FastAPI process.
  $hostExe = if (Get-Command pwsh.exe -ErrorAction SilentlyContinue) { "pwsh.exe" } else { "powershell.exe" }
  $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Port $Port"
  Start-Process $hostExe -Verb RunAs -ArgumentList $args
  exit
}

Set-Location $Root
$Py = Join-Path $Root "engine\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  python -m venv ".\engine\.venv"
}

& $Py -m pip install -e ".\engine[dev]"
$env:PYTHONPATH = "$Root\engine\src;$Root"

$token = (& $Py -c "from app.security import API_TOKEN; print(API_TOKEN)").Trim()

Write-Host ""
Write-Host "NexuFlow FastAPI" -ForegroundColor Magenta
Write-Host "URL:   http://127.0.0.1:$Port/docs"
Write-Host "Token: $token" -ForegroundColor Yellow
try { Set-Clipboard -Value $token; Write-Host "Token copiado para a área de transferência." -ForegroundColor Green } catch {}
Write-Host ""

& $Py -m uvicorn app.api_server:app --host 127.0.0.1 --port $Port
