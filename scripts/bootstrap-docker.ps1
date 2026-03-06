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

function Start-DockerDesktop {
    try {
        Start-Process "docker-desktop:" -ErrorAction Stop | Out-Null
        return
    } catch {
        try {
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction Stop | Out-Null
            return
        } catch {
            Write-Host "[WARN] No se pudo abrir Docker Desktop automáticamente. Ábrelo manualmente." -ForegroundColor Yellow
        }
    }
}

function Get-DockerInfoResult {
    $output = ""
    try {
        $output = (& docker info 2>&1 | Out-String)
        if ($LASTEXITCODE -eq 0) {
            return @{ Success = $true; Output = $output }
        }
    } catch {
        $output = ($_ | Out-String)
    }
    return @{ Success = $false; Output = $output }
}

function Wait-DockerEngine {
    param(
        [int]$Attempts = 24,
        [int]$DelaySeconds = 5
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        $result = Get-DockerInfoResult
        if ($result.Success) {
            return @{ Ready = $true; Output = $result.Output }
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    $last = Get-DockerInfoResult
    return @{ Ready = $false; Output = $last.Output }
}

function Repair-DockerEngine {
    param([string]$LastOutput)

    Write-Host "[bootstrap] Intentando autorreparación de Docker Engine..." -ForegroundColor Cyan

    if ($LastOutput -match '500 Internal Server Error') {
        Write-Host "[bootstrap] Detectado error 500 del daemon." -ForegroundColor Yellow
    }
    if ($LastOutput -match 'dockerDesktopLinuxEngine|pipe') {
        Write-Host "[bootstrap] Detectado problema del pipe dockerDesktopLinuxEngine." -ForegroundColor Yellow
    }

    try {
        wsl --shutdown
        Write-Host "[bootstrap] WSL detenido (shutdown)." -ForegroundColor Cyan
    } catch {
        Write-Host "[WARN] No se pudo ejecutar wsl --shutdown." -ForegroundColor Yellow
    }

    try {
        Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
    } catch {
        # no-op
    }

    if (Test-IsAdmin) {
        try {
            $svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
            if ($null -ne $svc) {
                Restart-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
            }
        } catch {
            Write-Host "[WARN] No se pudo reiniciar com.docker.service." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[INFO] Sin privilegios de admin: se omite reinicio de servicio com.docker.service." -ForegroundColor DarkYellow
    }

    Start-DockerDesktop
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
    Start-DockerDesktop
}

Write-Host "[bootstrap] Esperando a que Docker Engine esté disponible..." -ForegroundColor Cyan

$waitResult = Wait-DockerEngine -Attempts 24 -DelaySeconds 5
$ready = $waitResult.Ready

if (-not $ready) {
    Repair-DockerEngine -LastOutput $waitResult.Output
    Write-Host "[bootstrap] Reintentando conexión al Docker Engine..." -ForegroundColor Cyan
    $waitResult2 = Wait-DockerEngine -Attempts 18 -DelaySeconds 5
    $ready = $waitResult2.Ready

    if (-not $ready) {
        Write-Host "[WARN] Docker Engine aún no responde." -ForegroundColor Yellow
        Write-Host "Salida de diagnóstico (resumen):" -ForegroundColor Yellow
        if ($waitResult2.Output) {
            $short = $waitResult2.Output
            if ($short.Length -gt 600) { $short = $short.Substring(0, 600) + "..." }
            Write-Host $short -ForegroundColor DarkYellow
        }
        Write-Host "Siguiente paso: reinicia la VM y vuelve a ejecutar bootstrap." -ForegroundColor Yellow
        Write-Host "Luego ejecuta: .\scripts\preflight-docker.ps1" -ForegroundColor Yellow
        exit 3
    }
}

Write-Host "[OK] Docker Engine activo. Ejecutando preflight final..." -ForegroundColor Green
& "$PSScriptRoot\preflight-docker.ps1"
exit $LASTEXITCODE
