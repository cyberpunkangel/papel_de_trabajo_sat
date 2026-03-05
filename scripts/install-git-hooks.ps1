$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

git config core.hooksPath .githooks

Write-Host 'Hooks activados correctamente usando .githooks' -ForegroundColor Green
Write-Host 'Siguiente paso: realiza un push de prueba para validar el pre-push.' -ForegroundColor Yellow
