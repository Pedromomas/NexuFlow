$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

if (-not (Test-Path ".\node_modules")) {
  npm install
}

Write-Host "Inicie .\scripts\run-api.ps1 em outro terminal para telemetria e operações Windows." -ForegroundColor Yellow
npm run ionic:serve
