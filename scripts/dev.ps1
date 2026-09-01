param([switch]$Elevated)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."

function Test-NexuFlowAdministrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-NexuFlowAdministrator)) {
  $PowerShellExe = if ($PSVersionTable.PSEdition -eq 'Core') {
    (Get-Process -Id $PID).Path
  } else {
    Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
  }
  Write-Host "O Windows pedira uma autorizacao unica para abrir o NexuFlow." -ForegroundColor Cyan
  Start-Process -FilePath $PowerShellExe -Verb RunAs -WorkingDirectory $Root -ArgumentList @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', "`"$PSCommandPath`"",
    '-Elevated'
  )
  exit 0
}

Set-Location $Root
& ".\scripts\doctor.ps1" -Desktop
& ".\scripts\build-engine.ps1"
if (-not (Test-Path ".\node_modules")) { npm install }
npm run dev
