param(
    [switch]$AutoInstallUbuntu,
    [switch]$SkipDockerDesktopStart
)

$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "[bootstrap] Preparando Docker en Windows..." -ForegroundColor Cyan

if (-not (Test-Command -Name 'wsl')) {
    if (-not (Test-IsAdmin)) {
        Write-Host "[ERROR] WSL no está disponible y se requieren permisos de administrador para instalarlo." -ForegroundColor Red
        Write-Host "Abre PowerShell como Administrador y ejecuta: wsl --install" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[bootstrap] Instalando WSL..." -ForegroundColor Cyan
    wsl --install
    Write-Host "[INFO] Reinicia Windows/VM y vuelve a ejecutar este script." -ForegroundColor Yellow
    exit 2
}

Write-Host "[bootstrap] Actualizando WSL..." -ForegroundColor Cyan
try {
    wsl --update
} catch {
    Write-Host "[WARN] No se pudo actualizar WSL automáticamente. Continúo con verificación." -ForegroundColor Yellow
}

$distrosRaw = wsl -l -q 2>$null
$distros = @($distrosRaw | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

if ($distros.Count -eq 0) {
    Write-Host "[WARN] No hay distribuciones WSL instaladas." -ForegroundColor Yellow
    if ($AutoInstallUbuntu) {
        Write-Host "[bootstrap] Instalando Ubuntu en WSL..." -ForegroundColor Cyan
        wsl --install -d Ubuntu
        Write-Host "[INFO] Reinicia Windows/VM y vuelve a ejecutar este script." -ForegroundColor Yellow
        exit 2
    }
    Write-Host "Ejecuta: wsl --install -d Ubuntu" -ForegroundColor Yellow
    exit 2
}

if (-not (Test-Command -Name 'docker')) {
    Write-Host "[ERROR] Docker CLI no está instalado. Instala Docker Desktop y vuelve a intentar." -ForegroundColor Red
    exit 1
}

if (-not $SkipDockerDesktopStart) {
    Write-Host "[bootstrap] Intentando abrir Docker Desktop..." -ForegroundColor Cyan
    try {
        Start-Process "docker-desktop:" -ErrorAction Stop | Out-Null
    } catch {
        try {
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction Stop | Out-Null
        } catch {
            Write-Host "[WARN] No se pudo abrir Docker Desktop automáticamente. Ábrelo manualmente." -ForegroundColor Yellow
        }
    }
}

Write-Host "[bootstrap] Esperando a que Docker Engine esté disponible..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 24; $i++) {
    try {
        docker info 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
    } catch {
        # no-op
    }
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    Write-Host "[WARN] Docker Engine aún no responde." -ForegroundColor Yellow
    Write-Host "Abre Docker Desktop y espera 'Engine running'." -ForegroundColor Yellow
    Write-Host "Luego ejecuta: .\scripts\preflight-docker.ps1" -ForegroundColor Yellow
    exit 3
}

Write-Host "[OK] Docker Engine activo. Ejecutando preflight final..." -ForegroundColor Green
& "$PSScriptRoot\preflight-docker.ps1"
exit $LASTEXITCODE
