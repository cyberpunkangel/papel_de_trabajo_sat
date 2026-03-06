# SAT - Descarga Masiva (Python)

Aplicación en **Python/FastAPI** para descarga masiva de CFDI y retenciones, con interfaz web y generación de reportes.

## Guía rápida para principiantes (Local, sin Docker)

Si quieres empezar desde cero sin complicaciones, usa el bootstrap local.

1) Instala Python 3.10+
- Windows: descarga Python desde su sitio oficial y marca la opción de agregar a `PATH` durante la instalación.
- Linux: instala `python3`, `python3-venv` y `pip` con tu gestor de paquetes.

2) Ejecuta bootstrap (un solo comando)

Windows (CMD):

```cmd
scripts\bootstrap-local.cmd
```

Windows (PowerShell):

```powershell
.\scripts\bootstrap-local.ps1
```

Linux/macOS (bash):

```bash
bash ./scripts/bootstrap-local.sh
```

- El bootstrap crea `.venv`, instala dependencias y precrea `config/*.json` locales desde los `.example` si aún no existen.

3) Inicia la aplicación

Windows:

```cmd
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Linux/macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Abre: <http://127.0.0.1:8000>

### Atajo: bootstrap + ejecutar en un paso

Windows (PowerShell):

```powershell
.\scripts\bootstrap-local.ps1 -Run
```

Linux/macOS (bash):

```bash
bash ./scripts/bootstrap-local.sh --run
```

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`

## Configuración local

El bootstrap crea, si no existen:

- `config/fiel_config.json`
- `config/contribuyente_data.json`
- `config/tabulador_isr.json`

También crea/prepara el entorno virtual `.venv` con todas las dependencias.

Si necesitas crear los archivos manualmente:

```bash
cp config/fiel_config.example.json config/fiel_config.json
cp config/contribuyente_data.example.json config/contribuyente_data.json
cp config/tabulador_isr.example.json config/tabulador_isr.json
```

En Windows PowerShell:

```powershell
Copy-Item config/fiel_config.example.json config/fiel_config.json
Copy-Item config/contribuyente_data.example.json config/contribuyente_data.json
Copy-Item config/tabulador_isr.example.json config/tabulador_isr.json
```

Edita `config/fiel_config.json` con rutas válidas para tu sistema operativo y después captura el resto desde la interfaz.

## Estructura principal

- `app/main.py`: entrada principal FastAPI.
- `app/routes/`: endpoints de API.
- `app/sat/`: lógica SAT (autenticación, consulta, verificación, descarga).
- `templates/` y `assets/`: interfaz web.
- `reporting/`: generación de reportes.

## Configuración

- `config/fiel_config.example.json`: plantilla de configuración FIEL.
- `config/contribuyente_data.example.json`: plantilla de datos de contribuyente.
- `config/tabulador_isr.example.json`: plantilla de tabulador ISR.

Los archivos reales `config/*.json` se consideran locales/sensibles y están excluidos del versionado.

## Publicación segura en GitHub

Antes de publicar:

1. Verifica que no salgan archivos sensibles en `git status`.
2. Revisa que no existan secretos o datos personales en el staging:

```bash
git diff --cached
git grep -nE "(BEGIN [A-Z ]*PRIVATE KEY|password|token|api[_-]?key|[A-Z]{3,4}[0-9]{6}[A-Z0-9]{3})"
```

3. Confirma que no estés incluyendo artefactos locales:
	- `fiel-uploads/`
	- `descargas/`
	- `reportes/`
	- `storage/`
	- `config/*.json`

Si en el pasado llegaste a commitear datos sensibles, rota credenciales y limpia historial antes de abrir el repositorio públicamente.

### Hook pre-push (recomendado)

Este repositorio incluye un hook `pre-push` que bloquea envíos con rutas sensibles o posibles secretos.

Activación en Windows PowerShell:

```powershell
./scripts/install-git-hooks.ps1
```

Activación en Ubuntu/Linux:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-push
```

El hook se versiona en `.githooks/pre-push` y valida, entre otros:
- archivos sensibles versionados (`fiel-uploads/`, `descargas/`, `reportes/`, `storage/`, `config/*.json`)
- presencia de llaves privadas/tokens en archivos de configuración
