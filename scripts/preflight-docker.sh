#!/usr/bin/env bash

set -euo pipefail

echo "[preflight] Verificando Docker..."

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker CLI no está instalado o no está en PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] Docker Compose no está disponible."
  echo "Instala Docker Compose o Docker Desktop."
  exit 1
fi

docker_info_output=""
if ! docker_info_output="$(docker info 2>&1)"; then
  echo "[WARN] Docker Engine no está corriendo o no es accesible."

  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if echo "$docker_info_output" | grep -qi "permission denied"; then
      echo "Parece un problema de permisos del socket Docker."
      echo "Sugerencia: sudo usermod -aG docker \$USER"
      echo "Luego cierra sesión e inicia sesión de nuevo."
      exit 2
    fi

    if command -v systemctl >/dev/null 2>&1; then
      echo "Sugerencia: sudo systemctl start docker"
      echo "Opcional: sudo systemctl enable docker"
    else
      echo "Sugerencia: inicia manualmente el servicio Docker de tu distro."
    fi
  else
    echo "Abre Docker Desktop y espera a que el engine esté en estado Running."
  fi

  exit 3
fi

echo "[OK] Todo listo para ejecutar: docker compose up -d --build"
exit 0
