$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python 3.12+ não encontrado."
}
python -c "import sys; assert sys.version_info >= (3,12), 'Python 3.12+ required'"

$Venv = Join-Path $Root "engine\.venv"
$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
  Write-Host "Criando ambiente Python isolado..." -ForegroundColor Cyan
  python -m venv $Venv
}

$SitePackages = Join-Path $Venv "Lib\site-packages"
Get-ChildItem $SitePackages -Filter "__editable__.nexuflow_engine-*.pth" -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem $SitePackages -Filter "nexuflow_engine-*.dist-info" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Remove-Item (Join-Path $Root "engine\src\nexuflow_engine.egg-info") -Recurse -Force -ErrorAction SilentlyContinue

& $Py -m pip install --upgrade pip
& $Py -m pip install -e ".\engine[dev]"
& $Py -c "import pathlib,nexus_engine; assert nexus_engine.__version__ == '1.5.7', nexus_engine.__version__; assert pathlib.Path(nexus_engine.__file__).resolve().is_relative_to(pathlib.Path(r'$Root\engine\src').resolve()), nexus_engine.__file__"
$PytestTemp = Join-Path $Root ".pytest-tmp"
Remove-Item -Recurse -Force $PytestTemp -ErrorAction SilentlyContinue
& $Py -m pytest .\engine\tests .\app\tests --basetemp="$PytestTemp" -q
if ($LASTEXITCODE -ne 0) { throw "Testes do engine falharam; build interrompido." }

Remove-Item -Recurse -Force .\engine\build, .\engine\dist -ErrorAction SilentlyContinue
& $Py -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --noupx `
  --name nexus-engine `
  --paths ".\engine\src" `
  --add-data ".\engine\src\nexus_engine\data;data" `
  ".\engine\src\nexus_engine\__main__.py" `
  --distpath ".\engine\dist" `
  --workpath ".\engine\build"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou; build interrompido." }

$Target = ".\src-tauri\binaries\nexus-engine-x86_64-pc-windows-msvc.exe"
New-Item -ItemType Directory -Force (Split-Path $Target) | Out-Null
Copy-Item ".\engine\dist\nexus-engine.exe" $Target -Force
Write-Host "Engine pronto: $Target" -ForegroundColor Green
