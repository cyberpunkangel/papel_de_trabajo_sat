param(
    [switch]$Run,
    [string]$BindHost = "127.0.0.1",
    [int]$BindPort = 8000,
    [bool]$AutoInstallPython = $true
)

$ErrorActionPreference = 'Stop'

function Test-PythonVersion {
    param([string]$PythonExe)

    try {
        $versionText = (& $PythonExe -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null).Trim()
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

function Resolve-ExistingPython {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and (Test-PythonVersion -PythonExe $pythonCmd.Source)) {
        return $pythonCmd.Source
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $candidates = @()
        try {
            $pyList = & $pyCmd.Source -0p 2>$null
            foreach ($line in $pyList) {
                if ($line -match '^[\s]*-[Vv]:(?<ver>\d+\.\d+)[^\s]*\s+\*?\s*(?<path>.+python\.exe)\s*$') {
                    $ver = [version]($Matches['ver'] + '.0')
                    $path = $Matches['path'].Trim()
                    if (Test-Path $path) {
                        $candidates += [pscustomobject]@{ Version = $ver; Path = $path }
                    }
                }
            }
        } catch {
            # no-op
        }

        $valid = $candidates |
            Where-Object { $_.Version -ge [version]'3.10.0' } |
            Sort-Object Version -Descending |
            Select-Object -First 1

        if ($valid -and (Test-PythonVersion -PythonExe $valid.Path)) {
            return $valid.Path
        }
    }

    return $null
}

function Install-PythonIfNeeded {
    param([switch]$AutoInstall)

    $found = Resolve-ExistingPython
    if ($found) { return $found }

    if (-not $AutoInstall) {
        throw "No se encontró Python 3.10+ instalado. Instálalo o ejecuta este script con -AutoInstallPython."
    }

    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCmd) {
        throw "No se encontró Python 3.10+ y no hay winget para instalar automáticamente. Instálalo manualmente."
    }

    Write-Host "[bootstrap-local] No se detectó Python 3.10+. Instalando Python 3.11..." -ForegroundColor Yellow
    & $wingetCmd.Source install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements --silent

    $after = Resolve-ExistingPython
    if (-not $after) {
        throw "Python se instaló, pero no fue detectado en esta sesión. Cierra y abre la terminal, luego ejecuta de nuevo el bootstrap."
    }
    return $after
}

Write-Host "[bootstrap-local] Preparando entorno local..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host "[bootstrap-local] Creando entorno virtual (.venv)..." -ForegroundColor Cyan
    $pythonExe = Install-PythonIfNeeded -AutoInstall:$AutoInstallPython
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
