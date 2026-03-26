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
    """Devuelve la carpeta de trabajo para el periodo solicitado.

    Reglas:
    - Si existe una carpeta exacta ``descargas/<periodo>``, se usa esa.
    - Si no existe, pero hay exactamente una carpeta hija cuyo nombre inicia con
      el ejercicio (por ejemplo ``2023_algo``), se usa esa.
    - Si no hay coincidencias o hay varias coincidencias ambiguas, se lanza un
      error para evitar mezclar XML de otro ejercicio.
    """
    periodo = str(periodo).strip()
    base = Path(base_dir) if base_dir is not None else DESCARGAS_DIR
    if not base.exists():
        raise FileNotFoundError(f'La carpeta de descargas no existe: {base}')

    candidate = base / periodo
    if candidate.exists():
        return candidate

    matching_dirs = sorted(
        child for child in base.iterdir()
        if child.is_dir() and child.name != 'COMPARAR' and child.name.startswith(periodo)
    )

    if len(matching_dirs) == 1:
        return matching_dirs[0]

    if not matching_dirs:
        raise FileNotFoundError(
            f'No se encontraron descargas para el ejercicio {periodo} en {base}.'
        )

    matches = ', '.join(child.name for child in matching_dirs)
    raise ValueError(
        'Se encontraron varias carpetas de descargas para el ejercicio '
        f'{periodo}: {matches}. Organiza las descargas o selecciona un periodo '
        'con una carpeta única antes de generar el reporte.'
    )
