param(
  [switch]$Desktop
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

& ".\scripts\doctor.ps1" -Desktop:$Desktop

$Venv = Join-Path $Root "engine\.venv"
$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
  Write-Host "Criando ambiente Python..." -ForegroundColor Cyan
  python -m venv $Venv
}

# Editable installs from an older extracted copy can leave .pth files that put
# the wrong NexuFlow source tree first on sys.path. Remove only NexuFlow's own
# generated metadata before recreating the editable install.
$SitePackages = Join-Path $Venv "Lib\site-packages"
Get-ChildItem $SitePackages -Filter "__editable__.nexuflow_engine-*.pth" -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem $SitePackages -Filter "nexuflow_engine-*.dist-info" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Remove-Item (Join-Path $Root "engine\src\nexuflow_engine.egg-info") -Recurse -Force -ErrorAction SilentlyContinue

& $Py -m pip install --upgrade pip
& $Py -m pip install -e ".\engine[dev]"
& $Py -c "import pathlib,nexus_engine; assert nexus_engine.__version__ == '1.7.0', nexus_engine.__version__; assert pathlib.Path(nexus_engine.__file__).resolve().is_relative_to(pathlib.Path(r'$Root\engine\src').resolve()), nexus_engine.__file__"

Write-Host "Instalando dependências Angular/Ionic/Tauri..." -ForegroundColor Cyan
npm install

Write-Host "NexuFlow pronto para desenvolvimento." -ForegroundColor Green
