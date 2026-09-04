@echo off
setlocal
title NexuFlow - Criar chave segura do atualizador
cd /d "%~dp0"
echo ============================================================
echo NEXUFLOW - CHAVE DEFINITIVA DO ATUALIZADOR
echo ============================================================
echo.
echo A senha nao aparece enquanto voce digita. Isso e normal.
echo Use somente letras sem acento, numeros e simbolos; minimo 16 caracteres.
echo Nao envie a senha por chat e nao perca essa senha.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create-updater-key.ps1"
echo.
if errorlevel 1 (
  echo A chave nao foi criada. Leia a mensagem acima.
) else (
  echo Processo concluido. Pode fechar esta janela.
)
pause
