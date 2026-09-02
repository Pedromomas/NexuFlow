param([Parameter(Mandatory=$true)][string]$Path, [switch]$AllowUnsigned)
$ErrorActionPreference = 'Stop'
$resolved = (Resolve-Path $Path).Path
$cleanup = $null
if ([IO.Path]::GetExtension($resolved) -eq '.zip') {
  $cleanup = Join-Path ([IO.Path]::GetTempPath()) ("NexuFlow-verify-" + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $cleanup | Out-Null
  Expand-Archive -LiteralPath $resolved -DestinationPath $cleanup
  $root = $cleanup
} else { $root = $resolved }
try {
  $manifest = Get-ChildItem -LiteralPath $root -Filter 'MANIFEST*.sha256' -File -Recurse | Select-Object -First 1
  if (-not $manifest) { throw 'Manifest SHA-256 não encontrado.' }
  foreach ($line in Get-Content $manifest.FullName) {
    if ($line -notmatch '^([0-9a-fA-F]{64}) \*(.+)$') { throw "Linha inválida no manifesto: $line" }
    $expected = $Matches[1].ToLowerInvariant()
    $target = Join-Path $manifest.Directory.FullName ($Matches[2].Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Arquivo ausente: $($Matches[2])" }
    $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "Hash divergente: $($Matches[2])" }
  }
  $bad = Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.sys','.asi') -or $_.Name -match '(?i)WinRing0|inpoutx64|WinDivert|Npcap' }
  if ($bad) { throw 'No-Driver Contract violado no pacote.' }
  $installer = Get-ChildItem -LiteralPath $root -Filter '*.exe' -File -Recurse | Where-Object Name -Like '*Setup*' | Select-Object -First 1
  if ($installer) {
    $signature = Get-AuthenticodeSignature $installer.FullName
    if ($signature.Status -ne 'Valid' -and -not $AllowUnsigned) { throw 'Instalador sem assinatura Authenticode válida.' }
  }
  Write-Host 'Release verification: PASS'
} finally {
  if ($cleanup -and (Test-Path -LiteralPath $cleanup)) { Remove-Item -LiteralPath $cleanup -Recurse -Force }
}
