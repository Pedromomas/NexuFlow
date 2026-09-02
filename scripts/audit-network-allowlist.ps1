$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
$service = Get-Content (Join-Path $Root 'src\app\core\nexus.service.ts') -Raw
if ($service -notmatch "apiBase\s*=\s*'http://127\.0\.0\.1:8000/api/v1'") { throw 'Network allowlist: unexpected API base.' }
if ($service -notmatch "url\.origin\s*!==\s*this\.allowedApiOrigin") { throw 'Network allowlist: browser origin guard missing.' }
if ($service -match 'fetch\s*\(\s*[''"]https?://') { throw 'Network allowlist: direct remote fetch found.' }
$requirements = Get-Content (Join-Path $Root 'requirements.txt') -Raw
if ($requirements -match '(?im)^\s*(requests|httpx|aiohttp)\b') { throw 'Network allowlist: general-purpose remote HTTP client dependency found.' }
Write-Host 'Network allowlist contract: PASS (default deny, local API only)'
