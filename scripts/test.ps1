$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

& ".\scripts\anti-cheat-audit.ps1"

$Py = if ($env:NEXUFLOW_PYTHON) { $env:NEXUFLOW_PYTHON } else { Join-Path $Root "engine\.venv\Scripts\python.exe" }
if (-not (Test-Path $Py)) {
  throw "Ambiente Python não encontrado. Rode .\scripts\setup.ps1 primeiro."
}

$ExtraTestDeps = if ($env:NEXUFLOW_TEST_DEPS) { ";$($env:NEXUFLOW_TEST_DEPS)" } else { '' }
$env:PYTHONPATH = if ($env:NEXUFLOW_TEST_DEPS) { "$($env:NEXUFLOW_TEST_DEPS);$Root\engine\src;$Root" } else { "$Root\engine\src;$Root" }
$PytestTemp = Join-Path $Root ".pytest-tmp"
Remove-Item -Recurse -Force $PytestTemp -ErrorAction SilentlyContinue
& $Py -c "import pytest,sys; sys.exit(pytest.main(sys.argv[1:]))" .\engine\tests .\app\tests --basetemp="$PytestTemp" -q
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }

if (Test-Path ".\node_modules") {
  npm run test:web
  if ($LASTEXITCODE -ne 0) { throw 'Web tests failed.' }
} else {
  Write-Warning "node_modules não existe; testes web ignorados. Rode npm install."
}
