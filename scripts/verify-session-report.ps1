param([Parameter(Mandatory=$true)][string]$Report)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
$Py = Join-Path $Root 'engine\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Py)) { throw 'Ambiente local não encontrado. Execute scripts/setup.ps1.' }
$resolved = (Resolve-Path $Report).Path
$env:PYTHONPATH = "$Root\engine\src;$Root"
$json = & $Py -m nexus_engine --verify-report-file $resolved
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível verificar o relatório.' }
$result = $json | ConvertFrom-Json
if (-not $result.valid) { throw 'ASSINATURA INVÁLIDA: o relatório foi alterado ou está corrompido.' }
Write-Host 'ASSINATURA VÁLIDA: relatório íntegro e originado pela chave local indicada no arquivo.'
