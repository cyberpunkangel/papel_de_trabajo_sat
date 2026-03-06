#!/usr/bin/env bash

set -euo pipefail

echo "[start] Ejecutando bootstrap Docker..."
bash "$(dirname "$0")/bootstrap-docker.sh"

echo "[start] Levantando aplicación con Docker Compose..."
docker compose up -d --build

echo "[OK] Aplicación levantada en http://127.0.0.1:8000"
echo "[INFO] Para ver logs: docker compose logs -f"
echo "[INFO] Para detener: docker compose down"
