param(
  [Parameter(Mandatory = $true)][string]$ConfigPath
)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
$Config = Resolve-Path $ConfigPath
$raw = Get-Content -LiteralPath $Config -Raw
$settings = $raw | ConvertFrom-Json

$pubkey = [string]$settings.plugins.updater.pubkey
$endpoint = [string]$settings.plugins.updater.endpoints[0]
if (-not $pubkey -or $pubkey -match 'REPLACE_|PLACEHOLDER|EXAMPLE') { throw 'A chave pública definitiva do updater não foi configurada.' }
if ($endpoint -notmatch '^https://github\.com/[^/]+/[^/]+/releases/') { throw 'O endpoint deve ser um GitHub Release HTTPS oficial.' }
if ($settings.bundle.createUpdaterArtifacts -ne $true) { throw 'createUpdaterArtifacts precisa estar ativado.' }
if (-not $env:TAURI_SIGNING_PRIVATE_KEY) { throw 'TAURI_SIGNING_PRIVATE_KEY não está disponível no cofre do ambiente de release.' }
if (-not $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD) { throw 'TAURI_SIGNING_PRIVATE_KEY_PASSWORD não está disponível no cofre do ambiente de release.' }

Set-Location $Root
& npx tauri build --features signed-updater --config $Config
if ($LASTEXITCODE -ne 0) { throw "Build assinado do updater falhou ($LASTEXITCODE)." }
