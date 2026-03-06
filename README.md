# SAT - Descarga Masiva (Python)

Aplicación en **Python/FastAPI** para descarga masiva de CFDI y retenciones, con interfaz web y generación de reportes.

## Guía rápida para principiantes (Docker)

Si nunca has levantado un proyecto con Docker, sigue estos pasos en orden.

1) Instala Docker Desktop
- Descarga e instala Docker Desktop (incluye Docker Engine y Docker Compose).
- Reinicia tu equipo si el instalador lo solicita.
- Abre Docker Desktop y espera a que diga que está corriendo.

2) Verifica que Docker funciona
- Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
docker --version
docker compose version
```

- Si ambos comandos responden con una versión, todo está listo.

3) Levanta con un solo comando (recomendado)

Windows (CMD clásico):

```cmd
scripts\start-docker.cmd
```

Windows (PowerShell):

```powershell
.\scripts\start-docker.ps1
```

Linux/macOS (bash):

```bash
bash ./scripts/start-docker.sh
```

- Este comando ejecuta bootstrap + pre-chequeo + `docker compose up -d --build`.
- Si todo está bien, la app queda en <http://127.0.0.1:8000>.

4) Revisa que todo arrancó bien

```bash
docker compose logs -f
```

5) Detener la aplicación

```bash
docker compose down
```

### (Opcional) Ejecutar bootstrap/pre-chequeo por separado

Bootstrap:

Windows (PowerShell):

```powershell
.\scripts\bootstrap-docker.ps1
```

Windows (CMD clásico):

```cmd
scripts\bootstrap-docker.cmd
```

Linux/macOS (bash):

```bash
bash ./scripts/bootstrap-docker.sh
```

- El bootstrap intenta preparar el entorno y luego ejecuta el pre-chequeo final.
- En Windows puede instalar/actualizar WSL y validar distro.
- En Windows también intenta autorreparar errores del daemon (por ejemplo `docker info` con error 500/pipe).
- En Linux puede instalar Docker automáticamente en distribuciones comunes.

No necesitas ejecutar `docker info` manualmente: el bootstrap ya valida que el engine esté listo.

Pre-chequeo:

Windows (PowerShell):

```powershell
.\scripts\preflight-docker.ps1
```

Windows (CMD clásico):

```cmd
scripts\preflight-docker.cmd
```

Linux/macOS (bash):

```bash
bash ./scripts/preflight-docker.sh
```

- Los scripts validan Docker y que el engine esté corriendo.
- En Windows además valida WSL y que exista al menos una distro instalada.
- Si te falta la distro, también puedes pedir instalación automática:

```powershell
.\scripts\preflight-docker.ps1 -AutoInstallUbuntu
```

- Si instala Ubuntu, reinicia la VM y ejecuta de nuevo el bootstrap/pre-chequeo.

- Cuando ya no veas errores, abre tu navegador en: <http://127.0.0.1:8000>

Notas importantes:
- No necesitas instalar Python local para usar Docker.
- En el primer arranque, la app crea automáticamente archivos de configuración vacíos para que después los llenes desde la interfaz.

## Requisitos

- **Recomendado (Docker):**
  - Docker Engine + Docker Compose (o Docker Desktop)
  - No necesitas Python ni instalar dependencias localmente
- **Alternativa (modo local sin Docker):**
  - Python 3.10+
  - Dependencias en `requirements.txt`

## Inicio rápido (Docker, detallado)

1) Levanta la app:

```bash
docker compose up -d --build
```

2) Ver logs:

```bash
docker compose logs -f
```

3) Detener contenedor:

```bash
docker compose down
```

La app queda disponible en <http://127.0.0.1:8000>.

### Configuración local autogenerada

Al iniciar la aplicación (también con Docker), se crean automáticamente si no existen:

- `config/fiel_config.json` (vacío)
- `config/contribuyente_data.json` (vacío)
- `config/tabulador_isr.json` (con `{"periods": {}}`)
- carpetas locales: `fiel-uploads/`, `descargas/`, `reportes/`, `storage/`

Después, captura los datos desde la interfaz de la aplicación (cliente). Si editas manualmente `config/fiel_config.json`, usa rutas válidas para tu sistema operativo.

### (Opcional) Precrear archivos desde ejemplos

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

Notas:
- El contenedor usa volúmenes para `config`, `fiel-uploads`, `descargas`, `reportes` y `storage`.
- Tus datos locales no se empaquetan en la imagen.
- `config/fiel_config.json` sigue siendo local/ignorado por Git.

## Modo local (sin Docker)

### Instalación

Windows (PowerShell):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Ubuntu / Linux (bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Ejecución

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Abre: <http://127.0.0.1:8000>.

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
