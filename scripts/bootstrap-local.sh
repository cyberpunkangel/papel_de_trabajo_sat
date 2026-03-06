#!/usr/bin/env bash

set -euo pipefail

RUN_APP=false
HOST="127.0.0.1"
PORT="8000"
AUTO_INSTALL_PYTHON=true

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
    --no-auto-install-python)
      AUTO_INSTALL_PYTHON=false
      shift
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

version_is_valid() {
  local cmd="$1"
  local version
  version="$($cmd -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
  [[ -n "$version" ]] || return 1
  local major="${version%%.*}"
  local minor="${version##*.}"
  if (( major > 3 )); then return 0; fi
  if (( major == 3 && minor >= 10 )); then return 0; fi
  return 1
}

resolve_python_cmd() {
  if command -v python3 >/dev/null 2>&1 && version_is_valid python3; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1 && version_is_valid python; then
    echo "python"
    return 0
  fi
  return 1
}

install_python_if_needed() {
  local current
  if current="$(resolve_python_cmd 2>/dev/null)"; then
    echo "$current"
    return 0
  fi

  if [[ "$AUTO_INSTALL_PYTHON" != "true" ]]; then
    echo "[ERROR] No se encontró Python 3.10+ instalado."
    exit 1
  fi

  echo "[bootstrap-local] No se detectó Python 3.10+. Intentando instalar..."

  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y python3 python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm python python-pip
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install python3 python3-pip
  elif command -v brew >/dev/null 2>&1; then
    brew install python@3.11
  else
    echo "[ERROR] No se pudo instalar Python automáticamente en este sistema."
    exit 1
  fi

  if current="$(resolve_python_cmd 2>/dev/null)"; then
    echo "$current"
    return 0
  fi

  echo "[ERROR] Python se instaló, pero no fue detectado en esta sesión."
  echo "Cierra/abre terminal e inténtalo de nuevo."
  exit 1
}

if [[ ! -x "$VENV_PY" ]]; then
  echo "[bootstrap-local] Creando entorno virtual (.venv)..."
  PY_CMD="$(install_python_if_needed)"
  "$PY_CMD" -m venv "$VENV_DIR"
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
