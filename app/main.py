"""
FastAPI application entry point.
"""

import logging
import os

from fastapi import FastAPI

# Configure 'app' logger with its own handler so uvicorn's
# dictConfig doesn't swallow our INFO messages.
_app_logger = logging.getLogger('app')
_app_logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
_app_logger.addHandler(_handler)
_app_logger.propagate = False
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.routes import fiel, contribuyente, tabulador, downloads, sat, reports, packages
from app.config.bootstrap import ensure_local_runtime_files

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

app = FastAPI(
    title="Sistema de Declaracion Anual SAT",
    description="Descarga y procesa documentos fiscales de forma automatica",
    version="2.0.0",
)


@app.on_event("startup")
async def startup_bootstrap() -> None:
    ensure_local_runtime_files()

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(fiel.router, prefix="/api/fiel", tags=["FIEL"])
app.include_router(contribuyente.router, prefix="/api/contribuyente", tags=["Contribuyente"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["Downloads"])
app.include_router(sat.router, prefix="/api/sat", tags=["SAT"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(tabulador.router, prefix="/api/tabulador", tags=["Tabulador"])
app.include_router(packages.router, prefix="/api/packages", tags=["Packages"])

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
assets_dir = os.path.join(BASE_DIR, 'assets')
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
_template_path = os.path.join(BASE_DIR, 'templates', 'index.html')


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML page."""
    with open(_template_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())


if __name__ == '__main__':
    import sys
    import uvicorn
    # Ensure project root is in sys.path so 'app' package is importable
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        timeout_keep_alive=600,
    )
