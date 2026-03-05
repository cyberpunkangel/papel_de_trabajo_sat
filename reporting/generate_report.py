"""CLI para generar el reporte Excel a partir de los XML descargados."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reporting.config import (
    CONTRIBUYENTE_FILE,
    DEFAULT_OUTPUT_TEMPLATE,
    DESCARGAS_DIR,
    LOGS_DIR,
    REPORTS_DIR,
    resolve_data_root,
)
from reporting.models import Documento
from reporting.processors import (
    DeduccionesProcessor,
    DividendosProcessor,
    EnajenacionProcessor,
    InteresesProcessor,
    NominasProcessor,
)
from reporting.utils import ExcelWriter, setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generar reporte Excel a partir de los XML descargados del SAT')
    parser.add_argument('--descargas-dir', type=Path, default=DESCARGAS_DIR, help='Ruta a la carpeta "descargas" del proyecto')
    parser.add_argument('--output-dir', type=Path, default=REPORTS_DIR, help='Ruta donde se guardarán los reportes generados')
    parser.add_argument('--logs-dir', type=Path, default=LOGS_DIR, help='Ruta para almacenar los logs del proceso')
    parser.add_argument('--config-file', type=Path, default=CONTRIBUYENTE_FILE, help='Archivo JSON con los datos del contribuyente')
    parser.add_argument('--periodo', help='Periodo fiscal a procesar (por defecto se usa el guardado en el formulario)')
    parser.add_argument('--tabulador-isr', type=Path, help='Archivo JSON con el tabulador ISR capturado por el usuario')
    parser.add_argument('--console-log', action='store_true', help='Muestra el log también en consola')
    return parser.parse_args()


def load_contribuyente(config_file: Path) -> dict:
    if not config_file.exists():
        raise FileNotFoundError(
            f'No se encontró el archivo {config_file}. Guarda tus datos fiscales en la sección "Datos del Contribuyente" antes de generar el reporte.'
        )
    with config_file.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    required = ['nombre', 'rfc', 'curp', 'periodo']
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ValueError(f'Faltan datos del contribuyente: {", ".join(missing)}')
    return data


def gather_documentos(data_root: Path, contribuyente: dict) -> list[Documento]:
    receptor_rfc = (contribuyente.get('rfc') or '').strip().upper()
    processors = [
        NominasProcessor(data_root),
        DeduccionesProcessor(data_root, receptor_rfc=receptor_rfc),
        InteresesProcessor(data_root),
        DividendosProcessor(data_root),
        EnajenacionProcessor(data_root),
    ]
    documentos: list[Documento] = []
    for processor in processors:
        documentos.extend(processor.procesar())
    return documentos


def main() -> int:
    args = parse_args()
    logger = None
    try:
        contribuyente = load_contribuyente(args.config_file)
        periodo = args.periodo or contribuyente['periodo']

        descargas_dir = Path(args.descargas_dir)
        if not descargas_dir.exists():
            raise FileNotFoundError(f'La carpeta de descargas no existe: {descargas_dir}')

        data_root = resolve_data_root(periodo, base_dir=descargas_dir)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logs_dir = Path(args.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_logger('report_generator', logs_dir, console=args.console_log)
        logger.info('Iniciando generación del reporte para el periodo %s', periodo)
        logger.info('Datos del contribuyente: %s (%s)', contribuyente['nombre'], contribuyente['rfc'])
        logger.info('Carpeta analizada: %s', data_root)

        tabulador_isr = []
        if args.tabulador_isr:
            if not args.tabulador_isr.exists():
                raise FileNotFoundError(f'No se encontró el tabulador ISR en {args.tabulador_isr}')
            with args.tabulador_isr.open('r', encoding='utf-8') as handle:
                tabulador_isr = json.load(handle)

        documentos = gather_documentos(data_root, contribuyente)
        if not documentos:
            raise ValueError('No se encontraron XML para procesar en la carpeta de descargas seleccionada')

        output_filename = DEFAULT_OUTPUT_TEMPLATE.format(periodo=periodo)
        output_path = output_dir / output_filename
        contribuyente_reporte = dict(contribuyente)
        contribuyente_reporte['periodo'] = str(periodo)
        excel_writer = ExcelWriter(
            str(output_path),
            contribuyente_reporte,
            tabulador_isr=tabulador_isr,
        )
        excel_writer.crear_reporte(documentos)

        resumen = {
            'success': True,
            'message': 'Reporte generado correctamente',
            'output_file': str(output_path),
            'log_file': getattr(logger, 'log_file', ''),
            'periodo': periodo,
            'stats': {
                'nominas': sum(1 for d in documentos if d.tipo_ingreso == 'nomina12'),
                'intereses': sum(
                    1
                    for d in documentos
                    if d.tipo_ingreso not in {
                        'nomina12',
                        'dividendos',
                        'enajenaciondeacciones',
                        'deducciones_personales',
                    }
                ),
                'deducciones': sum(1 for d in documentos if d.tipo_ingreso == 'deducciones_personales'),
                'dividendos': sum(1 for d in documentos if d.tipo_ingreso == 'dividendos'),
                'enajenacion': sum(1 for d in documentos if d.tipo_ingreso == 'enajenaciondeacciones'),
                'total': len(documentos),
            },
        }

        print(json.dumps(resumen, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover - CLI
        log_file = getattr(logger, 'log_file', '') if logger else ''
        error_message = {
            'success': False,
            'message': str(exc),
            'log_file': log_file,
        }
        if logger:
            logger.exception('Fallo al generar el reporte')
        print(json.dumps(error_message, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
