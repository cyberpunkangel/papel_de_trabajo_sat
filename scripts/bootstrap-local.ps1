param(
    [switch]$Run,
    [string]$BindHost = "127.0.0.1",
    [int]$BindPort = 8000
)

$ErrorActionPreference = 'Stop'

function Test-PythonVersion {
    param([string]$PythonCmd)

    try {
        $versionText = (& $PythonCmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null).Trim()
        if (-not $versionText) { return $false }
        $parts = $versionText.Split('.')
        if ($parts.Length -lt 2) { return $false }
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return ($major -gt 3) -or ($major -eq 3 -and $minor -ge 10)
    } catch {
        return $false
    }
}

function Get-PythonCommand {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "No se encontró el comando 'python'. Instala Python 3.10+ y vuelve a intentar."
    }
    if (-not (Test-PythonVersion -PythonCmd $pythonCmd.Source)) {
        throw "La versión de Python detectada no es compatible. Requieres Python 3.10 o superior."
    }
    return $pythonCmd.Source
}

Write-Host "[bootstrap-local] Preparando entorno local..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host "[bootstrap-local] Creando entorno virtual (.venv)..." -ForegroundColor Cyan
    $pythonExe = Get-PythonCommand
    & $pythonExe -m venv $venvPath
}

Write-Host "[bootstrap-local] Instalando dependencias..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements.txt')

$configDir = Join-Path $projectRoot 'config'
New-Item -ItemType Directory -Force -Path $configDir | Out-Null

$configTemplates = @(
    @{ Example = 'fiel_config.example.json'; Target = 'fiel_config.json' },
    @{ Example = 'contribuyente_data.example.json'; Target = 'contribuyente_data.json' },
    @{ Example = 'tabulador_isr.example.json'; Target = 'tabulador_isr.json' }
)

foreach ($item in $configTemplates) {
    $source = Join-Path $configDir $item.Example
    $target = Join-Path $configDir $item.Target
    if ((Test-Path $source) -and -not (Test-Path $target)) {
        Copy-Item $source $target
    }
}

Write-Host "[OK] Entorno local listo." -ForegroundColor Green

if ($Run) {
    Write-Host "[bootstrap-local] Iniciando aplicación..." -ForegroundColor Cyan
    & $venvPython -m uvicorn app.main:app --host $BindHost --port $BindPort --reload
    exit $LASTEXITCODE
}

Write-Host "Siguiente paso:" -ForegroundColor DarkCyan
Write-Host ".\.venv\Scripts\python -m uvicorn app.main:app --host $BindHost --port $BindPort --reload" -ForegroundColor DarkCyan
exit 0
