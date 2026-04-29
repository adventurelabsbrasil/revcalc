#!/bin/bash
set -e

echo "================================================"
echo " Calculadora Crefaz - Instalacao e Teste (Mac) "
echo "================================================"
echo

if ! command -v brew >/dev/null 2>&1; then
  echo "[ERRO] Homebrew nao encontrado."
  echo "Instale em: https://brew.sh/"
  exit 1
fi

echo "[1/3] Instalando LibreOffice..."
brew install --cask libreoffice || true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH_1="$SCRIPT_DIR/../CalculadoraCrefaz.app"
APP_PATH_2="$SCRIPT_DIR/CalculadoraCrefaz.app"

echo
echo "[2/3] Verificando app..."
if [ -d "$APP_PATH_1" ]; then
  APP_PATH="$APP_PATH_1"
elif [ -d "$APP_PATH_2" ]; then
  APP_PATH="$APP_PATH_2"
else
  echo "[ERRO] CalculadoraCrefaz.app nao encontrado na pasta esperada."
  echo "Coloque o .app junto com este kit e rode novamente."
  exit 1
fi

echo "[3/3] Removendo quarentena e abrindo app..."
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true
open "$APP_PATH"

echo
echo "App aberto. Agora:"
echo "- Clique em \"Entrar com Google\""
echo "- Rode 1 cliente de teste"
echo "- Confirme os arquivos 10 Calculo, 12 Log e 13 Print no Drive"
echo
read -r -p "Pressione ENTER para finalizar..."
