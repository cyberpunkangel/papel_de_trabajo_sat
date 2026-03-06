#!/usr/bin/env bash

set -euo pipefail

RUN_APP=false
HOST="127.0.0.1"
PORT="8000"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run)
      RUN_APP=true
      shift
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      echo "Argumento no reconocido: $1"
      exit 1
      ;;
  esac
done

echo "[bootstrap-local] Preparando entorno local..."

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "[bootstrap-local] Creando entorno virtual (.venv)..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR"
  else
    echo "[ERROR] Python no está instalado. Instala Python 3.10+ y vuelve a intentar."
    exit 1
  fi
fi

echo "[bootstrap-local] Instalando dependencias..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"

mkdir -p "$ROOT_DIR/config"

copy_if_missing() {
  local example="$1"
  local target="$2"
  if [[ -f "$ROOT_DIR/config/$example" && ! -f "$ROOT_DIR/config/$target" ]]; then
    cp "$ROOT_DIR/config/$example" "$ROOT_DIR/config/$target"
  fi
}

copy_if_missing "fiel_config.example.json" "fiel_config.json"
copy_if_missing "contribuyente_data.example.json" "contribuyente_data.json"
copy_if_missing "tabulador_isr.example.json" "tabulador_isr.json"

echo "[OK] Entorno local listo."

if [[ "$RUN_APP" == "true" ]]; then
  echo "[bootstrap-local] Iniciando aplicación..."
  "$VENV_PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
  exit 0
fi

echo "Siguiente paso:"
echo ".venv/bin/python -m uvicorn app.main:app --host $HOST --port $PORT --reload"
