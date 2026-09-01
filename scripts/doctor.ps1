param(
  [switch]$Desktop
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$Name, [string]$Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name não encontrado. $Hint"
  }
}

Require-Command python "Instale Python 3.12+ (3.14 recomendado)."
Require-Command node "Instale uma versão do Node.js suportada pelo Angular 22."
Require-Command npm "npm deve acompanhar o Node.js."

python -c "import sys; assert sys.version_info >= (3,12), f'Python 3.12+ required, found {sys.version}'"

$nodeVersion = (node -p "process.versions.node").Trim()
$parts = $nodeVersion.Split('.') | ForEach-Object { [int]$_ }
$okNode = ($parts[0] -gt 22) -or ($parts[0] -eq 22 -and ($parts[1] -gt 22 -or ($parts[1] -eq 22 -and $parts[2] -ge 3)))
if (-not $okNode) {
  throw "Node.js $nodeVersion detectado. Angular 22 requer Node 22.22.3+ (ou uma linha mais nova suportada)."
}

if ($Desktop) {
  # $IsWindows exists only in PowerShell Core. This .NET check also works in
  # Windows PowerShell 5.1, which is still the default on many Windows PCs.
  if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "O host desktop Tauri do NexuFlow é destinado ao Windows 10/11."
  }
  Require-Command cargo "Instale Rust stable via rustup."
  Require-Command rustc "Instale Rust stable via rustup."

  $webView = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}' -ErrorAction SilentlyContinue
  if (-not $webView) {
    Write-Warning "WebView2 Runtime não foi detectado no registro. O Tauri pode solicitar/usar o runtime fornecido pelo Windows."
  }
}

Write-Host "Doctor OK: Python e Node/npm encontrados$(if($Desktop){'; Rust/Windows desktop prontos'}else{''})." -ForegroundColor Green
