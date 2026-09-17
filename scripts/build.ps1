param(
  [string]$CertificateThumbprint = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

& ".\scripts\anti-cheat-audit.ps1"

& ".\scripts\doctor.ps1" -Desktop
& ".\scripts\build-engine.ps1"

# Optional production signing. Signing the sidecar before Tauri bundling means
# the installed privileged helper is the signed binary, not an unsigned copy.
if ($CertificateThumbprint) {
  & ".\scripts\sign-file.ps1" `
    -Path ".\src-tauri\binaries\nexus-engine-x86_64-pc-windows-msvc.exe" `
    -CertificateThumbprint $CertificateThumbprint
}

npm install
if ($LASTEXITCODE -ne 0) { throw "Instalacao das dependencias falhou; nenhum instalador novo foi validado." }
npm run test:web
if ($LASTEXITCODE -ne 0) { throw "Testes da interface falharam; publicacao bloqueada." }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Compilacao falhou; nao distribuir instaladores antigos da pasta de saida." }

if ($CertificateThumbprint) {
  Get-ChildItem ".\src-tauri\target\release\bundle" -Recurse -Filter *.exe -ErrorAction SilentlyContinue |
    ForEach-Object {
      & ".\scripts\sign-file.ps1" -Path $_.FullName -CertificateThumbprint $CertificateThumbprint
    }
}

Write-Host "Build final em src-tauri\target\release\bundle\nsis" -ForegroundColor Green
