param(
    [switch]$Run,
    [string]$BindHost = "127.0.0.1",
    [int]$BindPort = 8000
)

$ErrorActionPreference = 'Stop'

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @('py', '-3')
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @('python')
    }
    throw "Python no está instalado. Instala Python 3.10+ y vuelve a intentar."
}

Write-Host "[bootstrap-local] Preparando entorno local..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host "[bootstrap-local] Creando entorno virtual (.venv)..." -ForegroundColor Cyan
    $pyCommand = Resolve-PythonCommand
    if ($pyCommand.Count -eq 2) {
        & $pyCommand[0] $pyCommand[1] -m venv $venvPath
    } else {
        & $pyCommand[0] -m venv $venvPath
    }
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
