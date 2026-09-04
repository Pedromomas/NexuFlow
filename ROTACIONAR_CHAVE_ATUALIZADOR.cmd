@echo off
setlocal
title NexuFlow - Substituir chave do atualizador
cd /d "%~dp0"
echo ============================================================
echo NEXUFLOW - NOVA CHAVE DO ATUALIZADOR
echo ============================================================
echo.
echo A chave anterior sera preservada. Nenhum arquivo sera sobrescrito.
echo Crie uma NOVA senha, diferente da anterior.
echo Use somente letras sem acento, numeros e simbolos; minimo 16 caracteres.
echo A senha nao aparece enquanto voce digita. Isso e normal.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create-updater-key.ps1" -PrivateKeyPath "%USERPROFILE%\Documents\NexuFlow-Secrets\nexuflow-updater-v2.key" -BackupDirectory "%USERPROFILE%\OneDrive\NexuFlow-Secrets-Backup"
echo.
if errorlevel 1 (
  echo A nova chave nao foi criada. Leia a mensagem acima.
) else (
  echo Nova chave criada. Nao apague a chave antiga ainda.
)
pause
