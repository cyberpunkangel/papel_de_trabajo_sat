param(
    [switch]$AutoInstallUbuntu
)

$ErrorActionPreference = 'Stop'

Write-Host "[start] Ejecutando bootstrap Docker..." -ForegroundColor Cyan
& "$PSScriptRoot\bootstrap-docker.ps1" @PSBoundParameters
if ($LASTEXITCODE -ne 0) {
    Write-Host "[start] Bootstrap no finalizó correctamente (exit $LASTEXITCODE)." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "[start] Levantando aplicación con Docker Compose..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo levantar la aplicación con Docker Compose." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[OK] Aplicación levantada en http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[INFO] Para ver logs: docker compose logs -f" -ForegroundColor DarkCyan
Write-Host "[INFO] Para detener: docker compose down" -ForegroundColor DarkCyan
exit 0
