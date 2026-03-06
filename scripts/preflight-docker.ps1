param(
    [switch]$AutoInstallUbuntu
)

$ErrorActionPreference = 'Stop'

Write-Host "[preflight] Verificando Docker y WSL..." -ForegroundColor Cyan

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command -Name 'docker')) {
    Write-Host "[ERROR] Docker CLI no está instalado o no está en PATH." -ForegroundColor Red
    exit 1
}

if (-not (Test-Command -Name 'wsl')) {
    Write-Host "[ERROR] WSL no está disponible en este sistema." -ForegroundColor Red
    Write-Host "Ejecuta (como admin): wsl --install" -ForegroundColor Yellow
    exit 1
}

try {
    $wslStatus = wsl --status 2>&1
    if ($LASTEXITCODE -ne 0) { throw "WSL status failed" }
} catch {
    Write-Host "[ERROR] WSL no está listo." -ForegroundColor Red
    Write-Host "Ejecuta (como admin): wsl --install" -ForegroundColor Yellow
    exit 1
}

$distrosRaw = wsl -l -q 2>$null
$distros = @($distrosRaw | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

if ($distros.Count -eq 0) {
    Write-Host "[WARN] No hay distribuciones WSL instaladas." -ForegroundColor Yellow
    if ($AutoInstallUbuntu) {
        Write-Host "[preflight] Instalando Ubuntu en WSL..." -ForegroundColor Cyan
        wsl --install -d Ubuntu
        Write-Host "[INFO] Reinicia Windows/VM y vuelve a ejecutar este script." -ForegroundColor Yellow
        exit 2
    }
    Write-Host "Instala una distro (ejemplo): wsl --install -d Ubuntu" -ForegroundColor Yellow
    exit 2
}

try {
    $dockerInfoOutput = (& docker info 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "docker info failed" }
} catch {
    Write-Host "[WARN] Docker Engine no está corriendo." -ForegroundColor Yellow
    if ($dockerInfoOutput -match '500 Internal Server Error|dockerDesktopLinuxEngine|pipe') {
        Write-Host "[INFO] Se detectó un problema del daemon (500/pipe)." -ForegroundColor DarkYellow
    }
    Write-Host "Abre Docker Desktop, espera 'Engine running' y vuelve a intentar." -ForegroundColor Yellow
    Write-Host "Sugerencia automática: .\scripts\bootstrap-docker.ps1" -ForegroundColor Yellow
    exit 3
}

Write-Host "[OK] Todo listo para ejecutar: docker compose up -d --build" -ForegroundColor Green
exit 0
