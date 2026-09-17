param(
  [string]$OutputPath = "$PSScriptRoot\..\SBOM.cdx.json",
  [string]$Python = "python"
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$lockText = Get-Content (Join-Path $ProjectRoot 'package-lock.json') -Raw
# Windows PowerShell 5 cannot deserialize the empty root-package key.
# Rename that one metadata key; it is excluded from the dependency inventory.
$lock = ($lockText -replace '""\s*:\s*\{', '"__root_metadata__": {') | ConvertFrom-Json
$components = @{}
foreach ($property in $lock.packages.PSObject.Properties) {
  if ($property.Name -eq '__root_metadata__' -or -not $property.Name -or -not $property.Value.version) { continue }
  $name = ($property.Name -split 'node_modules/')[-1]
  $version = [string]$property.Value.version
  $purl = "pkg:npm/$($name.Replace('@','%40'))@$version"
  $components[$purl] = [ordered]@{ type='library'; name=$name; version=$version; purl=$purl; scope=$(if ($property.Value.dev) { 'optional' } else { 'required' }) }
}
$cargo = Get-Content (Join-Path $ProjectRoot 'src-tauri\Cargo.lock') -Raw
foreach ($match in [regex]::Matches($cargo, '(?ms)^\[\[package\]\]\s+name = "([^"]+)"\s+version = "([^"]+)"')) {
  $name = $match.Groups[1].Value; $version = $match.Groups[2].Value
  if ($name -eq 'nexuflow') { continue }
  $purl = "pkg:cargo/$name@$version"
  $components[$purl] = [ordered]@{ type='library'; name=$name; version=$version; purl=$purl }
}
$pythonPackages = & $Python -m pip list --format=json --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Cannot inventory installed Python packages.' }
foreach ($package in ($pythonPackages | ConvertFrom-Json)) {
  $name = ($package.name.ToLowerInvariant() -replace '[-_.]+','-')
  if ($name -eq 'nexuflow-engine') { continue }
  $purl = "pkg:pypi/$name@$($package.version)"
  $components[$purl] = [ordered]@{ type='library'; name=$name; version=$package.version; purl=$purl }
}
$version = (Get-Content (Join-Path $ProjectRoot 'package.json') -Raw | ConvertFrom-Json).version
$document = [ordered]@{
  bomFormat='CycloneDX'; specVersion='1.5'; serialNumber="urn:uuid:$([guid]::NewGuid())"; version=1
  metadata=[ordered]@{
    timestamp=[DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    component=[ordered]@{ type='application'; name='NexuFlow'; version=$version }
    properties=@(@{name='nexuflow:inventory-scope';value='npm lockfile, Cargo lockfile, installed Python build environment; includes build/test dependencies, not a binary reachability analysis'})
  }
  components=@($components.Keys | Sort-Object | ForEach-Object { $components[$_] })
}
$document | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "SBOM generated: $($components.Count) components"
