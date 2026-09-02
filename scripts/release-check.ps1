param([switch]$SkipBuild, [switch]$AllowUnsigned)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

$Version = '1.5.8'
$ReleaseName = "NexuFlow-$Version-SecretArtEdition"
foreach ($f in @('package.json','engine\pyproject.toml','src-tauri\Cargo.toml','src-tauri\tauri.conf.json')) {
  if (-not (Select-String -Path $f -SimpleMatch $Version -Quiet)) { throw "Version mismatch: $f" }
}

& "$PSScriptRoot\audit-anticheat.ps1"
& "$PSScriptRoot\test.ps1"
& "$PSScriptRoot\generate-sbom.ps1"
if (-not $SkipBuild) { & "$PSScriptRoot\build.ps1" }

$Release = Join-Path $Root "release\$ReleaseName"
$SourceRelease = Join-Path $Root "release\$ReleaseName-Source"
foreach ($target in @($Release, $SourceRelease)) {
  if (Test-Path $target) { Remove-Item $target -Recurse -Force }
  New-Item -ItemType Directory -Force $target | Out-Null
}

$installer = Get-ChildItem (Join-Path $Root 'src-tauri\target\release\bundle\nsis') -Filter '*.exe' -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*$Version*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $installer) { throw "Instalador NSIS $Version não encontrado. Execute sem -SkipBuild." }
$signature = Get-AuthenticodeSignature $installer.FullName
if ($signature.Status -ne 'Valid' -and -not $AllowUnsigned) {
  throw 'O instalador não possui assinatura Authenticode válida. Use -AllowUnsigned apenas para build local de teste.'
}
if ($signature.Status -ne 'Valid') {
  Write-Warning 'Build local sem assinatura comercial: o Windows mostrará Fornecedor desconhecido. Isso não afeta os hashes.'
}

$consumerFiles = @(
  'docs\INSTALL.md','docs\RELEASE_1.5.8.md','docs\ANTI_CHEAT.md',
  'docs\VALIDATION.md','docs\SAFETY.md','LICENSE','SBOM.cdx.json'
)
foreach ($item in $consumerFiles) {
  $source = Join-Path $Root $item
  $destination = Join-Path $Release $item
  New-Item -ItemType Directory -Force (Split-Path $destination -Parent) | Out-Null
  Copy-Item $source $destination -Recurse -Force
}
Copy-Item $installer.FullName (Join-Path $Release "NexuFlow-$Version-Setup.exe") -Force

$sourceFiles = @(
  '.vscode','app\__init__.py','app\_bootstrap.py','app\api_server.py','app\schemas.py','app\security.py','app\modules','app\tests',
  'docs','engine\src\nexus_engine','engine\tests','engine\pyproject.toml','public','scripts','src',
  'src-tauri\capabilities','src-tauri\icons','src-tauri\src','src-tauri\Cargo.toml','src-tauri\Cargo.lock',
  'src-tauri\tauri.conf.json','src-tauri\build.rs','src-tauri\app.manifest','.gitignore','angular.json',
  'ionic.config.json','LICENSE','NexuFlow.code-workspace','nexus-engine.spec','package.json','package-lock.json',
  'postcss.config.mjs','README.md','requirements.txt','SBOM.cdx.json','tsconfig.json','tsconfig.app.json','tsconfig.spec.json'
)
foreach ($item in $sourceFiles) {
  $source = Join-Path $Root $item
  if (-not (Test-Path $source)) { throw "Source package item missing: $item" }
  $destination = Join-Path $SourceRelease $item
  New-Item -ItemType Directory -Force (Split-Path $destination -Parent) | Out-Null
  Copy-Item $source $destination -Recurse -Force
}

# Copy-Item preserves Python caches created by the test run. They are not
# source code, make reviews noisy, and may expose machine-specific bytecode.
# The target is the freshly recreated release staging directory above.
Get-ChildItem $SourceRelease -Recurse -Directory -Force |
  Where-Object { $_.Name -in @('__pycache__','.pytest_cache','.mypy_cache','.ruff_cache') } |
  Sort-Object { $_.FullName.Length } -Descending |
  Remove-Item -Recurse -Force
Get-ChildItem $SourceRelease -Recurse -File -Force |
  Where-Object { $_.Extension -in @('.pyc','.pyo') } |
  Remove-Item -Force

function Write-Manifest([string]$Folder, [string]$Name) {
  Get-ChildItem $Folder -Recurse -File | Sort-Object FullName | ForEach-Object {
    $relative = $_.FullName.Substring($Folder.Length + 1).Replace('\','/')
    "{0} *{1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $relative
  } | Set-Content (Join-Path $Folder $Name) -Encoding ascii
}
Write-Manifest $Release 'MANIFEST.sha256'
Write-Manifest $SourceRelease 'MANIFEST-SOURCE.sha256'

$zip = Join-Path $Root "release\$ReleaseName.zip"
$sourceZip = Join-Path $Root "release\$ReleaseName-Source.zip"
foreach ($archive in @($zip, $sourceZip)) {
  if (Test-Path $archive) { Remove-Item $archive -Force }
}
Compress-Archive -Path "$Release\*" -DestinationPath $zip -CompressionLevel Optimal
Compress-Archive -Path "$SourceRelease\*" -DestinationPath $sourceZip -CompressionLevel Optimal

function Write-ZipHash([string]$Archive) {
  $hash = (Get-FileHash $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
  Set-Content "$Archive.sha256" "$hash *$(Split-Path $Archive -Leaf)" -Encoding ascii
  return $hash
}
$zipHash = Write-ZipHash $zip
$sourceZipHash = Write-ZipHash $sourceZip

$outputs = Join-Path (Split-Path $Root -Parent | Split-Path -Parent) 'outputs'
New-Item -ItemType Directory -Force $outputs | Out-Null
foreach ($artifact in @($zip,"$zip.sha256",$sourceZip,"$sourceZip.sha256")) {
  Copy-Item $artifact (Join-Path $outputs (Split-Path $artifact -Leaf)) -Force
}
$installerOutput = Join-Path $outputs "NexuFlow-$Version-Setup-x64.exe"
Copy-Item $installer.FullName $installerOutput -Force
$installerHash = Write-ZipHash $installerOutput
Copy-Item (Join-Path $Release 'MANIFEST.sha256') (Join-Path $outputs "MANIFEST-$Version.sha256") -Force
Copy-Item (Join-Path $SourceRelease 'MANIFEST-SOURCE.sha256') (Join-Path $outputs "MANIFEST-$Version-SOURCE.sha256") -Force
Copy-Item (Join-Path $Root 'SBOM.cdx.json') (Join-Path $outputs "SBOM-$Version.cdx.json") -Force

Write-Host "APP SHA-256: $zipHash"
Write-Host "SOURCE SHA-256: $sourceZipHash"
Write-Host "INSTALLER SHA-256: $installerHash"
Write-Host "RELEASE CHECK PASS: $zip"
Write-Host "SOURCE RELEASE PASS: $sourceZip"
