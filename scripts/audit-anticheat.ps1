$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
& "$PSScriptRoot\anti-cheat-audit.ps1"

$Excluded = @('node_modules', 'target', '.venv', 'dist', '.git', '.pytest_cache', '.pytest-tmp')
$RuntimeFiles = Get-ChildItem $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
  $path = $_.FullName
  -not ($Excluded | Where-Object { $path -like "*\$_\*" })
}
$BadExtensions = $RuntimeFiles | Where-Object { $_.Extension -in @('.sys', '.asi') }
$BadNames = $RuntimeFiles | Where-Object { $_.Name -match '(?i)WinRing0|inpoutx64|WinDivert|Npcap|packet.*filter' }
if ($BadExtensions -or $BadNames) {
  throw "No-Driver Contract violated: custom/kernel/packet driver artifact found."
}
Write-Host 'No-Driver Contract: PASS'
