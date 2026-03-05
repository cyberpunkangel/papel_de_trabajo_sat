"""Configuración por defecto del generador de reportes."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESCARGAS_DIR = PROJECT_ROOT / 'descargas'
REPORTS_DIR = PROJECT_ROOT / 'reportes'
LOGS_DIR = PROJECT_ROOT / 'storage/reporting-logs'
CONTRIBUYENTE_FILE = PROJECT_ROOT / 'config/contribuyente_data.json'
DEFAULT_OUTPUT_TEMPLATE = 'Papel_de_Trabajo_Generado_{periodo}.xlsx'

NOMINA_DIR_NAMES = [
    'RECIBOS_DE_NOMINA',
    'RECIBOS DE NOMINA',
    'RECIBOS_NOMINA',
    'NOMINA',
    'NOMINAS',
]

RETENCION_DIR_NAMES = [
    'CONSTANCIAS_DE_RETENCIONES',
    'CONSTANCIAS DE RETENCIONES',
    'INTERESES, DIVIDENDOS, ENAJENACION DE ACCIONES',
    'RETENCIONES',
]

OTROS_CFDI_DIR_NAMES = [
    'OTROS_CFDI',
    'OTROS CFDI',
    'CFDI_RECIBIDOS',
]

def resolve_data_root(periodo: str | int, base_dir: Path | None = None) -> Path:
    """Devuelve la carpeta de trabajo para el periodo solicitado."""
    periodo = str(periodo)
    base = Path(base_dir) if base_dir is not None else DESCARGAS_DIR
    candidate = base / periodo
    if candidate.exists():
        return candidate
    return base
