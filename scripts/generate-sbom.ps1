$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
$Out = Join-Path $Root 'SBOM.cdx.json'
$pkgText = Get-Content (Join-Path $Root 'package-lock.json') -Raw
$cargo = Get-Content (Join-Path $Root 'src-tauri\Cargo.lock') -Raw
$components = New-Object System.Collections.ArrayList
$npmMatches = [regex]::Matches($pkgText, '(?ms)"node_modules/([^"]+)"\s*:\s*\{.*?"version"\s*:\s*"([^"]+)"')
foreach ($m in $npmMatches) { [void]$components.Add([pscustomobject][ordered]@{ type='library'; name=$m.Groups[1].Value; version=$m.Groups[2].Value; purl="pkg:npm/$($m.Groups[1].Value)@$($m.Groups[2].Value)" }) }
$cargoMatches = [regex]::Matches($cargo, '(?ms)^\[\[package\]\]\s+name = "([^"]+)"\s+version = "([^"]+)"')
foreach ($m in $cargoMatches) { [void]$components.Add([pscustomobject][ordered]@{ type='library'; name=$m.Groups[1].Value; version=$m.Groups[2].Value; purl="pkg:cargo/$($m.Groups[1].Value)@$($m.Groups[2].Value)" }) }
$requirements = Get-Content (Join-Path $Root 'requirements.txt') | Where-Object { $_ -and -not $_.StartsWith('#') }
foreach ($r in $requirements) {
  $req = [string]$r
  $reqName = [string](($req -split '[<>=~!]')[0])
  [void]$components.Add([pscustomobject][ordered]@{ type='library'; name=$reqName; version=$req; purl="pkg:pypi/$reqName" })
}
$doc = [pscustomobject][ordered]@{ bomFormat='CycloneDX'; specVersion='1.5'; serialNumber="urn:uuid:$([guid]::NewGuid())"; version=1; metadata=[pscustomobject][ordered]@{ component=[pscustomobject][ordered]@{ type='application'; name='NexuFlow'; version='1.5.5' } }; components=$components }
$doc | ConvertTo-Json -Depth 8 | Set-Content $Out -Encoding utf8
Write-Host "SBOM: $Out ($($components.Count) components)"
