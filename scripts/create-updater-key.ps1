param(
  [string]$PrivateKeyPath = "$env:USERPROFILE\Documents\NexuFlow-Secrets\nexuflow-updater.key",
  [string]$BackupDirectory = "$env:USERPROFILE\OneDrive\NexuFlow-Secrets-Backup"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$PrivateKeyPath = [System.IO.Path]::GetFullPath($PrivateKeyPath)
$BackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)

if ($PrivateKeyPath.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "A chave privada deve ficar fora do projeto."
}
if (-not $PrivateKeyPath.EndsWith(".key", [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Use a extensao .key para a chave privada."
}
if (Test-Path -LiteralPath $PrivateKeyPath) {
  throw "A chave ja existe. O script nunca sobrescreve a identidade do atualizador."
}

$PrimaryDirectory = Split-Path -Parent $PrivateKeyPath
New-Item -ItemType Directory -Force -Path $PrimaryDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null

Push-Location $ProjectRoot
try {
  Write-Host "Crie uma senha forte usando apenas letras sem acento, numeros e simbolos." -ForegroundColor Cyan
  Write-Host "A senha nao aparece enquanto voce digita. Isso e normal." -ForegroundColor Cyan

  $SecurePassword = Read-Host "Senha da chave" -AsSecureString
  $SecureConfirmation = Read-Host "Repita a senha" -AsSecureString
  $PasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
  $ConfirmationPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureConfirmation)

  try {
    $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPointer)
    $PlainConfirmation = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ConfirmationPointer)

    if ([string]::IsNullOrWhiteSpace($PlainPassword) -or $PlainPassword.Length -lt 16) {
      throw "A senha precisa ter pelo menos 16 caracteres."
    }
    if ($PlainPassword -cne $PlainConfirmation) {
      throw "As duas senhas nao sao iguais. Nenhuma chave foi criada."
    }
    if ($PlainPassword -notmatch '^[\x21-\x7E]+$') {
      throw "Use somente letras sem acento, numeros e simbolos comuns. Nao use espacos, acentos ou emoji."
    }

    & node ".\node_modules\@tauri-apps\cli\tauri.js" signer generate --password $PlainPassword --write-keys $PrivateKeyPath --ci
    if ($LASTEXITCODE -ne 0) { throw "O CLI do Tauri nao gerou a chave." }
  } finally {
    if ($PasswordPointer -ne [IntPtr]::Zero) {
      [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPointer)
    }
    if ($ConfirmationPointer -ne [IntPtr]::Zero) {
      [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ConfirmationPointer)
    }
    $PlainPassword = $null
    $PlainConfirmation = $null
    $SecurePassword = $null
    $SecureConfirmation = $null
  }
} finally {
  Pop-Location
}

$PublicKeyPath = "$PrivateKeyPath.pub"
if (-not (Test-Path -LiteralPath $PrivateKeyPath) -or -not (Test-Path -LiteralPath $PublicKeyPath)) {
  throw "O par nao foi criado por completo."
}

Copy-Item -LiteralPath $PrivateKeyPath -Destination (Join-Path $BackupDirectory (Split-Path -Leaf $PrivateKeyPath))
Copy-Item -LiteralPath $PublicKeyPath -Destination (Join-Path $BackupDirectory (Split-Path -Leaf $PublicKeyPath))

Write-Host "Par criado e backup copiado." -ForegroundColor Green
Write-Host "Privada: $PrivateKeyPath" -ForegroundColor Yellow
Write-Host "Backup: $BackupDirectory" -ForegroundColor Yellow
Write-Host "Publica: $PublicKeyPath" -ForegroundColor Cyan
Write-Host "Guarde a senha em um gerenciador e em uma recuperacao offline separada." -ForegroundColor Cyan
