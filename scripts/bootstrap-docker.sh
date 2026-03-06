#!/usr/bin/env bash

set -euo pipefail

echo "[bootstrap] Preparando Docker en Linux/macOS..."

is_linux=false
is_macos=false

case "$(uname -s)" in
  Linux*) is_linux=true ;;
  Darwin*) is_macos=true ;;
esac

have_sudo=false
if command -v sudo >/dev/null 2>&1; then
  have_sudo=true
fi

ensure_docker_linux() {
  if command -v docker >/dev/null 2>&1; then
    return 0
  fi

  echo "[WARN] Docker CLI no encontrado. Intentando instalar..."

  if command -v apt-get >/dev/null 2>&1; then
    $have_sudo && sudo apt-get update || apt-get update
    $have_sudo && sudo apt-get install -y docker.io docker-compose-v2 || apt-get install -y docker.io docker-compose-v2
  elif command -v dnf >/dev/null 2>&1; then
    $have_sudo && sudo dnf install -y docker docker-compose-plugin || dnf install -y docker docker-compose-plugin
  elif command -v yum >/dev/null 2>&1; then
    $have_sudo && sudo yum install -y docker docker-compose-plugin || yum install -y docker docker-compose-plugin
  elif command -v pacman >/dev/null 2>&1; then
    $have_sudo && sudo pacman -Sy --noconfirm docker docker-compose || pacman -Sy --noconfirm docker docker-compose
  elif command -v zypper >/dev/null 2>&1; then
    $have_sudo && sudo zypper --non-interactive install docker docker-compose || zypper --non-interactive install docker docker-compose
  else
    echo "[ERROR] No se detectó gestor de paquetes soportado para instalar Docker automáticamente."
    echo "Instala Docker manualmente y vuelve a ejecutar este script."
    exit 1
  fi
}

if $is_linux; then
  ensure_docker_linux

  if command -v systemctl >/dev/null 2>&1; then
    $have_sudo && sudo systemctl enable docker || true
    $have_sudo && sudo systemctl start docker || true
  fi

  if id -nG "$USER" | grep -qw docker; then
    :
  else
    if $have_sudo; then
      echo "[bootstrap] Agregando usuario al grupo docker..."
      sudo usermod -aG docker "$USER" || true
      echo "[INFO] Cierra sesión e inicia sesión de nuevo para aplicar permisos de grupo." 
    fi
  fi
fi

if $is_macos; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[ERROR] En macOS instala Docker Desktop manualmente y vuelve a ejecutar este script."
    exit 1
  fi
fi

echo "[bootstrap] Ejecutando preflight..."
bash "$(dirname "$0")/preflight-docker.sh"
