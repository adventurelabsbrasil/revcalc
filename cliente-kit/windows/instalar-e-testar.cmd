@echo off
setlocal
title Calculadora Crefaz - Instalacao Windows

echo ================================================
echo  Calculadora Crefaz - Instalacao e Teste (Win)
echo ================================================
echo.

where winget >nul 2>&1
if errorlevel 1 (
  echo [ERRO] winget nao encontrado.
  echo Atualize o App Installer da Microsoft Store e tente novamente.
  pause
  exit /b 1
)

echo [1/3] Instalando LibreOffice...
winget install --id TheDocumentFoundation.LibreOffice -e --source winget
if errorlevel 1 (
  echo [AVISO] Nao foi possivel instalar automaticamente o LibreOffice.
  echo Baixe manualmente em: https://www.libreoffice.org/download/
)

echo.
echo [2/3] Verificando app...
if exist "%~dp0..\CalculadoraCrefaz.exe" (
  set "APP=%~dp0..\CalculadoraCrefaz.exe"
) else if exist "%~dp0CalculadoraCrefaz.exe" (
  set "APP=%~dp0CalculadoraCrefaz.exe"
) else (
  echo [ERRO] CalculadoraCrefaz.exe nao encontrado na pasta esperada.
  echo Coloque o .exe junto com este kit e rode novamente.
  pause
  exit /b 1
)

echo [3/3] Abrindo app para teste...
start "" "%APP%"

echo.
echo App aberto. Agora:
echo - Clique em "Entrar com Google"
echo - Rode 1 cliente de teste
echo - Confirme os arquivos 10 Calculo, 12 Log e 13 Print no Drive
echo.
pause
