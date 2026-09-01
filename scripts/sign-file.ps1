param(
  [Parameter(Mandatory=$true)][string]$Path,
  [Parameter(Mandatory=$true)][string]$CertificateThumbprint,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
$Resolved = Resolve-Path $Path

$SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $SignTool) {
  $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
  $candidate = Get-ChildItem $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
  if (-not $candidate) { throw "signtool.exe não encontrado. Instale Windows SDK/Build Tools." }
  $SignToolPath = $candidate.FullName
} else {
  $SignToolPath = $SignTool.Source
}

& $SignToolPath sign /sha1 $CertificateThumbprint /fd SHA256 /td SHA256 /tr $TimestampUrl $Resolved.Path
if ($LASTEXITCODE -ne 0) { throw "Falha ao assinar $($Resolved.Path)" }
& $SignToolPath verify /pa /v $Resolved.Path
if ($LASTEXITCODE -ne 0) { throw "Assinatura não validou em $($Resolved.Path)" }
Write-Host "Assinado: $($Resolved.Path)" -ForegroundColor Green
