$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root
& ".\scripts\doctor.ps1" -Desktop

$Sidecar = Join-Path $Root "src-tauri\binaries\nexus-engine-x86_64-pc-windows-msvc.exe"
$NewestSource = Get-ChildItem (Join-Path $Root "engine\src") -Recurse -File |
  Sort-Object LastWriteTimeUtc -Descending |
  Select-Object -First 1
$NeedsEngineBuild = -not (Test-Path $Sidecar)
if (-not $NeedsEngineBuild -and $NewestSource) {
  $NeedsEngineBuild = $NewestSource.LastWriteTimeUtc -gt (Get-Item $Sidecar).LastWriteTimeUtc
}
if ($NeedsEngineBuild) {
  Write-Host "Codigo do motor mudou; reconstruindo uma vez..." -ForegroundColor Cyan
  & ".\scripts\build-engine.ps1"
} else {
  Write-Host "Motor pronto; iniciando sem recompilacao completa." -ForegroundColor Green
}
if (-not (Test-Path ".\node_modules")) { npm install }
npm run dev
