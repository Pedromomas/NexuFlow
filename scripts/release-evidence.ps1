param(
  [Parameter(Mandatory=$true)][string]$Installer,
  [string]$OutputDirectory = "$PSScriptRoot\..\outputs\release-evidence",
  [string]$Python = "python"
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$InstallerPath = (Resolve-Path -LiteralPath $Installer).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
& "$PSScriptRoot\generate-sbom.ps1" -OutputPath (Join-Path $OutputDirectory 'SBOM.cdx.json') -Python $Python
$hash = (Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
$name = [IO.Path]::GetFileName($InstallerPath)
$version = (Get-Content (Join-Path $ProjectRoot 'package.json') -Raw | ConvertFrom-Json).version
$signature = (Get-AuthenticodeSignature -LiteralPath $InstallerPath).Status.ToString()
"$hash *$name" | Set-Content -LiteralPath (Join-Path $OutputDirectory 'SHA256SUMS.txt') -Encoding ascii
$record = [ordered]@{
  version=$version; generated_at=[DateTime]::UtcNow.ToString('o'); installer=$name; sha256=$hash
  authenticode=$signature; channel=$(if ($version.Contains('-')) {'beta'} else {'stable'})
  repository_visibility='public'; real_upgrade_validated=$false; live_match_validated=$false
  clean_windows_matrix_validated=$false
  limitations=@('Automatic evidence is not a real upgrade or live-match test.', 'Installer bit-for-bit reproducibility is not claimed.')
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'release-evidence.json') -Encoding utf8
@"
# NexuFlow $version

Community pre-release: all implemented features are free. Not validated as a stable release.

Installer: $name
SHA-256: $hash
Authenticode: $signature

See docs/RELEASE_COMMUNITY_RC2.md and docs/STABLE_GATES.md for changes and pending physical checks.
The accompanying SBOM includes build/test dependencies; it is not a reachability analysis.
"@ | Set-Content -LiteralPath (Join-Path $OutputDirectory 'RELEASE-NOTES.md') -Encoding utf8
Write-Host "Evidence generated; physical validation is still pending."
