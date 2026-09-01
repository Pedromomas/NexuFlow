$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

Write-Host "NexuFlow anti-cheat static audit..." -ForegroundColor Cyan

# Runtime-only scan. These APIs/libraries are unnecessary for an optimizer and
# would materially increase anti-cheat interaction surface.
$RuntimeRoots = @(
  ".\engine\src\nexus_engine",
  ".\app\modules",
  ".\src-tauri\src"
)
$ForbiddenSymbols = @(
  "ReadProcessMemory",
  "WriteProcessMemory",
  "NtReadVirtualMemory",
  "NtWriteVirtualMemory",
  "VirtualAllocEx",
  "CreateRemoteThread",
  "SetWindowsHookEx",
  "SendInput",
  "WinDivert",
  "Npcap",
  "SharpPcap",
  "Detours"
)

$runtimeFiles = foreach ($rootPath in $RuntimeRoots) {
  if (Test-Path $rootPath) {
    Get-ChildItem $rootPath -Recurse -File | Where-Object {
      $_.Extension -in @(".py", ".rs", ".toml", ".json") -and
      $_.FullName -notmatch "\\__pycache__\\"
    }
  }
}

$violations = @()
foreach ($file in $runtimeFiles) {
  $content = Get-Content $file.FullName -Raw -ErrorAction Stop
  foreach ($symbol in $ForbiddenSymbols) {
    if ($content -match [regex]::Escape($symbol)) {
      $violations += "$($file.FullName): forbidden runtime symbol '$symbol'"
    }
  }
}

# CS2 must remain in Trusted Mode. The launch override is permitted as text in
# docs/UI warnings, but never in executable launch/configuration code.
$launchFiles = @(
  Get-ChildItem ".\src-tauri" -Recurse -File -Include *.rs,*.json,*.toml -ErrorAction SilentlyContinue
  Get-ChildItem ".\scripts" -Recurse -File -Include *.ps1 -ErrorAction SilentlyContinue
  Get-Item ".\package.json" -ErrorAction SilentlyContinue
) | Where-Object { $_ -and $_.FullName -notmatch "\\target\\" }
foreach ($file in $launchFiles) {
  $content = Get-Content $file.FullName -Raw -ErrorAction Stop
  $trustedModeOverride = "allow_" + "third_party_software"
  if ($content -match [regex]::Escape($trustedModeOverride)) {
    $violations += "$($file.FullName): CS2 Trusted Mode override is forbidden"
  }
}

# No custom kernel driver or injection payload belongs in the source package.
$binaryRisks = Get-ChildItem $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
  $_.Extension -in @(".sys", ".asi") -and
  $_.FullName -notmatch "\\(node_modules|target|\.venv|build|dist)\\"
}
foreach ($file in $binaryRisks) {
  $violations += "$($file.FullName): kernel/injection-style binary is forbidden"
}

# Keep common memory/injection/packet-manipulation frameworks out of dependency
# manifests. This is intentionally conservative for public builds.
$manifests = @(".\engine\pyproject.toml", ".\requirements.txt", ".\package.json")
$ForbiddenDependencies = @("pymem", "frida", "pydivert", "win-divert", "scapy", "pynput", "detours")
foreach ($manifest in $manifests) {
  if (-not (Test-Path $manifest)) { continue }
  $content = (Get-Content $manifest -Raw).ToLowerInvariant()
  foreach ($dependency in $ForbiddenDependencies) {
    if ($content -match "(^|[^a-z0-9_-])$([regex]::Escape($dependency))([^a-z0-9_-]|$)") {
      $violations += "$($manifest): forbidden anti-cheat-sensitive dependency '$dependency'"
    }
  }
}

if ($violations.Count -gt 0) {
  $violations | ForEach-Object { Write-Host $_ -ForegroundColor Red }
  throw "Anti-cheat static audit failed with $($violations.Count) violation(s)."
}

Write-Host "Anti-cheat static audit OK: no injection/memory-hook/packet-driver surface detected." -ForegroundColor Green
