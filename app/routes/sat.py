"""
SAT bulk-download routes with SSE streaming.

This is the most complex route module. It implements:
- Server-Sent Events (SSE) via StreamingResponse
- Date range splitting into <= 31-day chunks
- Turbo mode: batch queries + round-robin polling
- FechaPago XML filtering with lxml XPath
- Retenciones date shift (+1 year)
- Retry logic with adjustable seconds for 5002 errors
- ZIP extraction and optional XML pretty-printing
- Download logging to storage/download-logs/
"""

import asyncio
import json
import logging
import os
import re
import time
import zipfile
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse

from app.config.fiel_config import FielConfig
from app.sat.request_builder.fiel import Fiel
from app.sat.request_builder.fiel_request_builder import FielRequestBuilder
from app.sat.service import Service
from app.sat.services.query import QueryParameters
from app.sat.shared.date_time_period import DateTimePeriod
from app.sat.shared.enums import (
    DocumentStatus,
    DocumentType,
    DownloadType,
    RequestType,
)
from app.sat.shared.service_endpoints import ServiceEndpoints
from app.sat.web_client.httpx_web_client import HttpxWebClient

logger = logging.getLogger(__name__)

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SAT_MAX_QUERY_DAYS = 31

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _send_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_sat_today() -> datetime:
    """Return current datetime in America/Mexico_City (UTC-6 simplified)."""
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo('America/Mexico_City')
    except Exception:
        tz = timezone(timedelta(hours=-6))
    return datetime.now(tz)


def _shift_date_by_years(fecha: str, years: int) -> str:
    """Shift a date string (YYYY-MM-DD) by the given number of years."""
    try:
        dt_obj = datetime.strptime(fecha, '%Y-%m-%d')
        # Handle Feb 29 -> Feb 28 when target year isn't a leap year
        new_year = dt_obj.year + years
        try:
            shifted = dt_obj.replace(year=new_year)
        except ValueError:
            shifted = dt_obj.replace(year=new_year, day=28)
        return shifted.strftime('%Y-%m-%d')
    except Exception:
        return fecha


def _shift_date_by_days(fecha: str, days: int) -> str:
    """Shift a date string (YYYY-MM-DD) by the given number of days."""
    try:
        dt_obj = datetime.strptime(fecha, '%Y-%m-%d')
        shifted = dt_obj + timedelta(days=days)
        return shifted.strftime('%Y-%m-%d')
    except Exception:
        return fecha


def _normalize_custom_datetime(value: str, default_time: str) -> Tuple[str, str]:
    """Normalize date or datetime text to (YYYY-MM-DD, HH:MM:SS)."""
    raw = (value or '').strip()
    if not raw:
        return '', default_time

    normalized = raw.replace('T', ' ')
    formats = (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    )

    for fmt in formats:
        try:
            dt_obj = datetime.strptime(normalized, fmt)
            return dt_obj.strftime('%Y-%m-%d'), dt_obj.strftime('%H:%M:%S')
        except ValueError:
            continue

    fallback_date = normalized[:10]
    try:
        dt_obj = datetime.strptime(fallback_date, '%Y-%m-%d')
        return dt_obj.strftime('%Y-%m-%d'), default_time
    except ValueError:
        return '', default_time


def _retry_seconds_time(base_time: str, retry: int, retry_offset: int = 0, end_time: bool = False) -> str:
    """Build retry time preserving hour/minute and varying seconds."""
    try:
        parsed = datetime.strptime((base_time or '').strip(), '%H:%M:%S')
        hour, minute, second = parsed.hour, parsed.minute, parsed.second
    except Exception:
        hour, minute, second = (23, 59, 59) if end_time else (0, 0, 0)

    if end_time:
        next_second = max(0, min(59, second - retry - max(0, retry_offset)))
    else:
        next_second = (second + retry) % 60

    return f'{hour:02d}:{minute:02d}:{next_second:02d}'


def _add_one_calendar_year(dt_obj: datetime) -> datetime:
    """Add one calendar year preserving date/time (leap-year aware)."""
    try:
        return dt_obj.replace(year=dt_obj.year + 1)
    except ValueError:
        # Caso típico: 29-feb -> 28-feb en año no bisiesto
        return dt_obj.replace(year=dt_obj.year + 1, day=28)


def _split_date_range(
    fecha_inicio: str,
    fecha_fin: str,
    max_days: int = 31,
) -> List[Dict[str, str]]:
    """Split a date range into chunks of at most *max_days* days each."""
    try:
        inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
    except Exception:
        return [{'inicio': fecha_inicio, 'fin': fecha_fin}]

    if inicio > fin:
        inicio, fin = fin, inicio

    max_days = max(1, max_days)
    chunks: List[Dict[str, str]] = []
    current = inicio

    while current <= fin:
        chunk_end = current + timedelta(days=max(0, max_days - 1))
        if chunk_end > fin:
            chunk_end = fin
        chunks.append({
            'inicio': current.strftime('%Y-%m-%d'),
            'fin': chunk_end.strftime('%Y-%m-%d'),
        })
        current = chunk_end + timedelta(days=1)

    return chunks


def _last_day_of_month(year: int, month: int) -> str:
    """Return the last day of the given month as YYYY-MM-DD."""
    _, last_day = monthrange(year, month)
    return f'{year:04d}-{month:02d}-{last_day:02d}'


def _format_xml_pretty(file_path: str) -> None:
    """Reformat an XML file with indentation (best-effort)."""
    try:
        from lxml import etree
        tree = etree.parse(file_path)
        etree.indent(tree)
        tree.write(
            file_path, xml_declaration=True, encoding='UTF-8', pretty_print=True
        )
    except Exception:
        pass


def _filter_xml_files_by_fecha_pago(
    base_dir: str,
    fecha_inicio: str,
    fecha_fin: str,
) -> Dict[str, int]:
    """Remove nomina XML files whose FechaPago falls outside the range."""
    result = {'evaluated': 0, 'removed': 0}
    if not os.path.isdir(base_dir):
        return result

    try:
        inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fin = datetime.strptime(fecha_fin, '%Y-%m-%d').replace(
            hour=23, minute=59, second=59
        )
    except Exception:
        return result

    if inicio > fin:
        inicio, fin = fin, inicio

    try:
        from lxml import etree
    except ImportError:
        return result

    ns = {'nomina12': 'http://www.sat.gob.mx/nomina12'}

    for dirpath, _dirs, filenames in os.walk(base_dir):
        for filename in filenames:
            if not filename.lower().endswith('.xml'):
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                tree = etree.parse(filepath)
                nomina_nodes = tree.xpath('//nomina12:Nomina', namespaces=ns)
                if not nomina_nodes:
                    continue

                fecha_pago_attr = nomina_nodes[0].get('FechaPago', '')
                if not fecha_pago_attr:
                    continue

                fecha_pago = datetime.strptime(fecha_pago_attr[:10], '%Y-%m-%d')
                result['evaluated'] += 1

                if fecha_pago < inicio or fecha_pago > fin:
                    os.unlink(filepath)
                    result['removed'] += 1
            except Exception:
                continue

    return result


def _save_retry_history(rfc: str, key: str, intent_data: dict) -> None:
    """Save retry intent data to the history file (best-effort)."""
    history_file = os.path.join(BASE_DIR, 'descargas', '.retry_history.json')
    try:
        history: dict = {}
        if os.path.isfile(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f) or {}

        if rfc not in history:
            history[rfc] = {}
        history[rfc][key] = intent_data

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def _get_retry_history(rfc: str, key: str) -> Optional[dict]:
    """Retrieve retry history for a given rfc/key."""
    history_file = os.path.join(BASE_DIR, 'descargas', '.retry_history.json')
    try:
        if not os.path.isfile(history_file):
            return None
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f) or {}
        return history.get(rfc, {}).get(key)
    except Exception:
        return None


def _append_download_log(rfc: str, payload: dict) -> None:
    """Append a log event to storage/download-logs/YYYY-MM-DD.log (best-effort)."""
    try:
        log_dir = os.path.join(BASE_DIR, 'storage', 'download-logs')
        os.makedirs(log_dir, exist_ok=True)

        now = _get_sat_today()
        log_file = os.path.join(log_dir, now.strftime('%Y-%m-%d') + '.log')

        event = {
            'ts': now.isoformat(),
            'endpoint': 'sat/download/stream',
            'rfc': rfc,
            **payload,
        }

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    except Exception:
        pass


def _extract_zip_packages(
    zip_data: bytes,
    output_dir: str,
    package_id: str,
    pretty_xml: bool,
) -> int:
    """Write zip_data to disk, extract XML files, optionally pretty-print, return count."""
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, f'{package_id}.zip')

    with open(zip_path, 'wb') as f:
        f.write(zip_data)

    total_files = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            xml_entries = [
                n for n in zf.namelist()
                if n.lower().endswith('.xml')
            ]

            if xml_entries:
                zf.extractall(output_dir, xml_entries)
                total_files = len(xml_entries)
            else:
                zf.extractall(output_dir)
                total_files = len(zf.namelist())

        os.unlink(zip_path)

        if pretty_xml and xml_entries:
            for entry_name in xml_entries:
                entry_path = os.path.join(
                    output_dir, entry_name.replace('\\', '/')
                )
                if os.path.isfile(entry_path):
                    _format_xml_pretty(entry_path)
    except Exception:
        if os.path.isfile(zip_path):
            try:
                os.unlink(zip_path)
            except OSError:
                pass

    return total_files


def _resolve_output_dir(
    base_dir: str,
    document_type_name: str,
    document_status: str,
) -> str:
    """Build the output directory path applying status subfolder rules."""
    subfolder = ''
    if document_status == 'active':
        subfolder = '/VIGENTES'
    elif document_status == 'cancelled':
        subfolder = '/CANCELADAS'

    output_dir = os.path.join(base_dir, document_type_name + subfolder)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# ---------------------------------------------------------------------------
# Core download logic (async generators for real-time SSE streaming)
# ---------------------------------------------------------------------------

async def _download_documents_sse(
    service: Service,
    fecha_inicio: str,
    fecha_fin: str,
    document_type: Optional[DocumentType],
    base_dir: str,
    document_type_name: str,
    document_status: str,
    hora_inicio: str = '00:00:00',
    hora_fin: str = '23:59:59',
    pretty_xml: bool = False,
    rfc: str = '',
    current_progress: int = 15,
    ctx: Optional[Dict] = None,
) -> AsyncGenerator[str, None]:
    """Perform query -> verify -> download for a single date range.
    Yields SSE event strings in real-time.
    Updates ctx dict with 'files' and 'progress' on completion.
    """
    if ctx is None:
        ctx = {}
    ctx.update({'files': 0, 'progress': current_progress})

    output_dir = _resolve_output_dir(base_dir, document_type_name, document_status)

    # Create period
    periodo = DateTimePeriod.create_from_values(
        f'{fecha_inicio} {hora_inicio}',
        f'{fecha_fin} {hora_fin}',
    )

    # Build query parameters
    query_params = (
        QueryParameters.create(periodo)
        .with_download_type(DownloadType.received())
        .with_request_type(RequestType.xml())
    )

    if document_status == 'active':
        query_params = query_params.with_document_status(DocumentStatus.active())
    elif document_status == 'cancelled':
        query_params = query_params.with_document_status(DocumentStatus.cancelled())
    elif document_status == 'both':
        query_params = query_params.with_document_status(DocumentStatus.active())

    if document_type is not None:
        query_params = query_params.with_document_type(document_type)

    yield _send_event('progress', {
        'percent': current_progress + 2,
        'message': 'Enviando consulta al SAT...',
    })

    # Execute query
    query = await service.query(query_params)

    if not query.get_status().is_accepted():
        error_msg = query.get_status().get_message()
        status_code = query.get_status().get_code()

        # 5004 = no data in period (not an error)
        if status_code == 5004 or '5004' in str(error_msg):
            logger.info('[%s] %s %s->%s: sin datos (5004)',
                        rfc, document_type_name, fecha_inicio, fecha_fin)
            _append_download_log(rfc, {
                'event': 'no_data_query',
                'status_code': status_code,
                'message': error_msg,
                'document_type_name': document_type_name,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            })
            yield _send_event('progress', {
                'percent': min(current_progress + 1, 90),
                'message': (
                    f'{document_type_name}: sin informacion en el periodo '
                    f'(CodigoEstadoSolicitud={status_code}).'
                ),
            })
            return

        raise Exception(f'Error {status_code}: {error_msg}')

    request_id = query.get_request_id()
    logger.info('[%s] %s consulta aceptada ID=%s (%s -> %s)',
                rfc, document_type_name, request_id, fecha_inicio, fecha_fin)

    _append_download_log(rfc, {
        'event': 'query_accepted',
        'request_id': request_id,
        'document_type_name': document_type_name,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'hora_inicio': hora_inicio,
        'hora_fin': hora_fin,
    })

    yield _send_event('progress', {
        'percent': current_progress + 3,
        'message': f'Consulta aceptada - ID: {request_id}',
    })
    current_progress += 3

    # Verify loop
    max_intentos = 90 if document_type_name == 'CONSTANCIAS_DE_RETENCIONES' else 60
    intento = 0
    verificado = None
    last_verify_status = None

    while True:
        wait = 2 if intento < 3 else (3 if intento < 8 else 5)
        await asyncio.sleep(wait)
        verificado = await service.verify(request_id)
        intento += 1

        status_request = verificado.get_status_request()
        code_request = verificado.get_code_request()
        number_cfdis = verificado.get_number_cfdis()

        if code_request.is_empty_result():
            yield _send_event('progress', {
                'percent': min(current_progress + 1, 90),
                'message': (
                    f'{document_type_name}: sin informacion en el periodo '
                    f'(CodigoEstadoSolicitud={code_request.get_value()}).'
                ),
            })
            return

        should_emit = (
            intento == 1
            or last_verify_status is None
            or status_request.get_value() != last_verify_status
            or intento % 5 == 0
        )
        last_verify_status = status_request.get_value()

        if should_emit:
            extra = f' | CFDI: {number_cfdis}' if number_cfdis > 0 else ''
            logger.info('[%s] %s verificacion #%d: %s%s',
                        rfc, document_type_name, intento,
                        status_request.get_message(), extra)
            yield _send_event('progress', {
                'percent': min(current_progress + 1, 90),
                'message': f'Verificacion #{intento} - {status_request.get_message()}{extra}',
            })

        if status_request.is_rejected() or status_request.is_failure():
            if code_request.is_empty_result():
                yield _send_event('progress', {
                    'percent': min(current_progress + 1, 90),
                    'message': (
                        f'{document_type_name}: sin informacion en el periodo '
                        f'(CodigoEstadoSolicitud={code_request.get_value()}).'
                    ),
                })
                return

            error_suffix = (
                f' (EstadoSolicitud {status_request.get_value()} '
                f'| CodigoEstadoSolicitud {code_request.get_value()})'
            )
            raise Exception(
                f'La solicitud fallo{error_suffix}: {status_request.get_message()}'
            )

        if status_request.is_finished():
            break

        if intento >= max_intentos:
            raise Exception('Tiempo de espera agotado')

    # Download packages
    package_ids = verificado.get_packages_ids()
    if not package_ids:
        return

    logger.info('[%s] %s descargando %d paquete(s)...',
                rfc, document_type_name, len(package_ids))
    yield _send_event('progress', {
        'percent': current_progress + 5,
        'message': f'Descargando {len(package_ids)} paquete(s)...',
    })
    current_progress += 5

    total_files = 0
    for package_id in package_ids:
        download_result = await service.download(package_id)
        extracted = _extract_zip_packages(
            download_result.get_package_content(),
            output_dir,
            package_id,
            pretty_xml,
        )
        total_files += extracted
        logger.info('[%s] %s paquete %s: %d archivo(s)',
                    rfc, document_type_name, package_id, extracted)

    ctx.update({'files': total_files, 'progress': current_progress})


async def _download_with_retry(
    service: Service,
    document_type: Optional[DocumentType],
    document_type_name: str,
    fecha_inicio: str,
    fecha_fin: str,
    document_status: str,
    base_dir: str,
    rfc: str,
    retry_offset: int = 0,
    pretty_xml: bool = False,
    current_progress: int = 15,
    custom_fecha_inicio: Optional[str] = None,
    custom_fecha_fin: Optional[str] = None,
    base_hora_inicio: str = '00:00:00',
    base_hora_fin: str = '23:59:59',
    ctx: Optional[Dict] = None,
) -> AsyncGenerator[str, None]:
    """Download documents with retry logic for 5002 errors.
    Yields SSE event strings in real-time.
    Updates ctx dict with 'archivos', 'reintentos', 'progress'.
    """
    if ctx is None:
        ctx = {}
    max_retries = 20
    consulta_inicio = custom_fecha_inicio or fecha_inicio
    consulta_fin = custom_fecha_fin or fecha_fin
    doc_type_val = document_type.value if document_type else 'RET'
    retry_key = f'{consulta_inicio}_{consulta_fin}_{doc_type_val}_{document_status}'
    reintentos_usados = 0
    es_primer_intento = True

    history = _get_retry_history(rfc, retry_key)
    start_retry = (history or {}).get('ultimo_intento', 0)

    for retry in range(start_retry, max_retries):
        hora_inicio = _retry_seconds_time(base_hora_inicio, retry)
        hora_fin = _retry_seconds_time(
            base_hora_fin,
            retry,
            retry_offset=retry_offset,
            end_time=True,
        )

        if not es_primer_intento:
            yield _send_event('retry', {
                'attempt': retry + 1,
                'max': max_retries,
                'message': f'Reintento {retry + 1} de {max_retries} (ajustando parametros...)',
            })
            current_progress += 1
            yield _send_event('progress', {
                'percent': min(current_progress, 95),
                'message': f'Reintento {retry + 1} de {max_retries}',
            })
            reintentos_usados += 1
        elif retry > 0:
            yield _send_event('progress', {
                'percent': min(current_progress + 1, 95),
                'message': f'Reanudando desde el intento {retry + 1}',
            })

        es_primer_intento = False

        try:
            inner_ctx: Dict = {}
            async for ev in _download_documents_sse(
                service,
                consulta_inicio,
                consulta_fin,
                document_type,
                base_dir,
                document_type_name,
                document_status,
                hora_inicio,
                hora_fin,
                pretty_xml,
                rfc,
                current_progress,
                ctx=inner_ctx,
            ):
                yield ev

            current_progress = inner_ctx.get('progress', current_progress)

            _save_retry_history(rfc, retry_key, {
                'ultimo_intento': retry,
                'intentos': retry + 1,
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'exito': True,
                'parametros': f'{consulta_inicio} {hora_inicio} - {consulta_fin} {hora_fin}',
            })

            ctx.update({
                'archivos': inner_ctx.get('files', 0),
                'reintentos': reintentos_usados,
                'progress': current_progress,
            })
            return

        except Exception as e:
            error_msg = str(e)

            _append_download_log(rfc, {
                'event': 'exception',
                'retry': retry + 1,
                'retry_key': retry_key,
                'message': error_msg,
            })

            # 5004 = no data (not an error, don't retry)
            if '5004' in error_msg:
                _save_retry_history(rfc, retry_key, {
                    'ultimo_intento': retry,
                    'intentos': retry + 1,
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'exito': True,
                    'archivos': 0,
                    'parametros': f'{consulta_inicio} {hora_inicio} - {consulta_fin} {hora_fin}',
                })
                ctx.update({
                    'archivos': 0,
                    'reintentos': reintentos_usados,
                    'progress': current_progress,
                })
                return

            # 5002 = exhausted parameters, retry with different seconds
            is_5002 = (
                '5002' in error_msg
                or 'agotado' in error_msg.lower()
                or 'por vida' in error_msg.lower()
            )
            if is_5002:
                _save_retry_history(rfc, retry_key, {
                    'ultimo_intento': retry + 1,
                    'intentos': retry + 1,
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'exito': False,
                    'error': 'Error 5002 - Parametros duplicados',
                })
                if retry < max_retries - 1:
                    continue
                else:
                    raise Exception(
                        'LIMITE DE REINTENTOS ALCANZADO\n\n'
                        'Se intento con diferentes parametros pero el SAT '
                        'sigue rechazando.\n\n'
                        'Soluciones:\n'
                        '- Espera 24 horas\n'
                        '- Intenta con un rango de fechas diferente\n'
                        '- Contacta al SAT si el problema persiste'
                    )
            else:
                raise

    ctx.update({
        'archivos': 0,
        'reintentos': reintentos_usados,
        'progress': current_progress,
    })


async def _download_chunks_turbo(
    service: Service,
    chunks: List[Dict[str, str]],
    document_type: Optional[DocumentType],
    base_dir: str,
    document_type_name: str,
    document_status: str,
    rfc: str,
    retry_offset: int = 0,
    pretty_xml: bool = False,
    label: str = 'Lote',
    current_progress: int = 15,
    base_hora_inicio: str = '00:00:00',
    base_hora_fin: str = '23:59:59',
    ctx: Optional[Dict] = None,
) -> AsyncGenerator[str, None]:
    """Turbo mode: batch queries, round-robin polling, parallel downloads.
    Yields SSE event strings in real-time.
    Updates ctx dict with 'archivos', 'peticiones_realizadas', 'reintentos', 'progress'.
    """
    if ctx is None:
        ctx = {}
    output_dir = _resolve_output_dir(base_dir, document_type_name, document_status)

    max_retries = 20
    accepted: List[Dict] = []
    total_retries = 0
    total_requests = 0
    total_files = 0

    yield _send_event('progress', {
        'percent': min(current_progress + 1, 95),
        'message': f'Modo turbo {label}: enviando {len(chunks)} consultas...',
    })

    # Phase 1: Submit queries
    for index, chunk in enumerate(chunks):
        consulta_inicio = chunk['inicio']
        consulta_fin = chunk['fin']
        doc_type_val = document_type.value if document_type else 'RET'
        retry_key = f'{consulta_inicio}_{consulta_fin}_{doc_type_val}_{document_status}'

        history = _get_retry_history(rfc, retry_key)
        start_retry = (history or {}).get('ultimo_intento', 0)
        accepted_request_id = None

        for retry in range(start_retry, max_retries):
            hora_inicio = _retry_seconds_time(base_hora_inicio, retry)
            hora_fin = _retry_seconds_time(
                base_hora_fin,
                retry,
                retry_offset=retry_offset,
                end_time=True,
            )

            try:
                periodo = DateTimePeriod.create_from_values(
                    f'{consulta_inicio} {hora_inicio}',
                    f'{consulta_fin} {hora_fin}',
                )

                query_params = (
                    QueryParameters.create(periodo)
                    .with_download_type(DownloadType.received())
                    .with_request_type(RequestType.xml())
                )

                if document_status in ('active', 'both'):
                    query_params = query_params.with_document_status(
                        DocumentStatus.active()
                    )
                elif document_status == 'cancelled':
                    query_params = query_params.with_document_status(
                        DocumentStatus.cancelled()
                    )

                if document_type is not None:
                    query_params = query_params.with_document_type(document_type)

                query = await service.query(query_params)
                query_status = query.get_status()

                if not query_status.is_accepted():
                    error_msg = query_status.get_message()
                    status_code = query_status.get_code()

                    # 5004 = empty, skip this chunk
                    if status_code == 5004 or '5004' in str(error_msg):
                        logger.info('[%s] %s turbo %s->%s: sin datos (5004)',
                                    rfc, document_type_name,
                                    consulta_inicio, consulta_fin)
                        _save_retry_history(rfc, retry_key, {
                            'ultimo_intento': retry,
                            'intentos': retry + 1,
                            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'exito': True,
                            'archivos': 0,
                        })
                        total_requests += 1
                        break  # go to next chunk

                    # 5002 = exhausted, try next seconds offset
                    is_5002 = (
                        '5002' in str(error_msg)
                        or 'agotado' in str(error_msg).lower()
                        or 'por vida' in str(error_msg).lower()
                    )
                    if is_5002:
                        total_retries += 1
                        if retry < max_retries - 1:
                            continue
                        # else fall through to raise

                    raise Exception(f'Error {status_code}: {error_msg}')

                accepted_request_id = query.get_request_id()
                logger.info('[%s] %s turbo %d/%d aceptado ID=%s (%s -> %s)',
                            rfc, document_type_name, index + 1, len(chunks),
                            accepted_request_id, consulta_inicio, consulta_fin)
                accepted.append({
                    'request_id': accepted_request_id,
                    'inicio': consulta_inicio,
                    'fin': consulta_fin,
                    'intentos_verifica': 0,
                    'started_at': time.time(),
                })

                _save_retry_history(rfc, retry_key, {
                    'ultimo_intento': retry,
                    'intentos': retry + 1,
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'exito': True,
                    'request_id': accepted_request_id,
                })

                total_requests += 1
                yield _send_event('progress', {
                    'percent': min(current_progress + 1, 95),
                    'message': (
                        f'{label} {index + 1}/{len(chunks)} aceptado '
                        f'({consulta_inicio} -> {consulta_fin})'
                    ),
                })
                break

            except Exception as e:
                if retry >= max_retries - 1:
                    raise
                total_retries += 1

        if (
            accepted_request_id is None
            and not (history or {}).get('exito', False)
        ):
            raise Exception(
                f'No se pudo enviar la consulta turbo para '
                f'{document_type_name} {consulta_inicio} -> {consulta_fin}'
            )

    if not accepted:
        ctx.update({
            'archivos': 0,
            'peticiones_realizadas': total_requests,
            'reintentos': total_retries,
            'progress': current_progress,
        })
        return

    yield _send_event('progress', {
        'percent': min(current_progress + 2, 95),
        'message': (
            f'Modo turbo {label}: verificando '
            f'{len(accepted)} solicitud(es) en cola...'
        ),
    })

    # Phase 2: Polling + Download
    base_verify_seconds = (
        900 if document_type_name == 'CONSTANCIAS_DE_RETENCIONES' else 600
    )
    extra_per_chunk = (
        60 if document_type_name == 'CONSTANCIAS_DE_RETENCIONES' else 45
    )
    chunk_count = max(1, len(chunks))
    max_verify_seconds = min(
        2700,
        base_verify_seconds + ((chunk_count - 1) * extra_per_chunk),
    )

    logger.info(
        '[%s] %s turbo timeout de verificacion=%ss (chunks=%d)',
        rfc,
        document_type_name,
        max_verify_seconds,
        chunk_count,
    )

    while accepted:
        keys_to_remove = []
        for idx, request_info in enumerate(accepted):
            request_info['intentos_verifica'] += 1
            try:
                verify = await service.verify(request_info['request_id'])
            except Exception as verify_exc:
                logger.warning(
                    'Turbo verify error (intento %d) para %s -> %s: %s',
                    request_info['intentos_verifica'],
                    request_info['inicio'], request_info['fin'],
                    verify_exc,
                )
                # Skip this request on this iteration, retry on next loop
                continue

            status_request = verify.get_status_request()
            code_request = verify.get_code_request()

            if code_request.is_empty_result():
                keys_to_remove.append(idx)
                continue

            if status_request.is_rejected() or status_request.is_failure():
                error_suffix = (
                    f' (EstadoSolicitud {status_request.get_value()} '
                    f'| CodigoEstadoSolicitud {code_request.get_value()})'
                )
                raise Exception(
                    f'La solicitud turbo fallo{error_suffix}: '
                    f'{status_request.get_message()}'
                )

            if status_request.is_finished():
                package_ids = verify.get_packages_ids()
                for package_id in package_ids:
                    download_result = await service.download(package_id)
                    extracted = _extract_zip_packages(
                        download_result.get_package_content(),
                        output_dir,
                        package_id,
                        pretty_xml,
                    )
                    total_files += extracted
                    logger.info('[%s] %s turbo paquete %s: %d archivo(s)',
                                rfc, document_type_name, package_id, extracted)

                yield _send_event('progress', {
                    'percent': min(current_progress + 4, 95),
                    'message': (
                        f'{label} listo '
                        f'({request_info["inicio"]} -> {request_info["fin"]})'
                    ),
                })
                keys_to_remove.append(idx)
                continue

            elapsed = time.time() - request_info.get('started_at', time.time())
            if elapsed >= max_verify_seconds:
                raise Exception(
                    f'Tiempo de espera agotado en modo turbo para '
                    f'{document_type_name} '
                    f'({request_info["inicio"]} -> {request_info["fin"]})'
                )

        # Remove completed entries (reverse order to preserve indices)
        for idx in sorted(keys_to_remove, reverse=True):
            accepted.pop(idx)

        if accepted:
            oldest_elapsed = max(
                (time.time() - info.get('started_at', time.time()))
                for info in accepted
            )
            poll_sleep = 5 if oldest_elapsed >= 240 else 3
            await asyncio.sleep(poll_sleep)

    ctx.update({
        'archivos': total_files,
        'peticiones_realizadas': total_requests,
        'reintentos': total_retries,
        'progress': current_progress,
    })


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------

@router.post("/download/stream")
async def download_stream(
    tipo_descarga: str = Form('anio_completo'),
    anio: str = Form(''),
    mes: str = Form('1'),
    fecha_inicio: str = Form(''),
    fecha_fin: str = Form(''),
    doc_nomina: str = Form('0'),
    doc_retenciones: str = Form('0'),
    doc_ingresos: str = Form('0'),
    document_status: str = Form('both'),
    fiel_password: str = Form(''),
    filter_fecha_pago: str = Form('1'),
    pretty_xml: str = Form('0'),
    turbo_mode: str = Form('1'),
):
    """SSE streaming endpoint for SAT bulk download.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield _send_event('progress', {
                'percent': 5,
                'message': 'Validando credenciales FIEL...',
            })

            # Parse parameters
            anio_clean = re.sub(r'[^0-9]', '', anio or '') or datetime.now().strftime('%Y')
            mes_clean = re.sub(r'[^0-9]', '', mes or '1').zfill(2)
            want_nomina = doc_nomina == '1'
            want_retenciones = doc_retenciones == '1'
            want_ingresos = doc_ingresos == '1'
            want_filter = filter_fecha_pago == '1'
            want_pretty = pretty_xml == '1'
            want_turbo = turbo_mode == '1'

            # Compute date range
            fi = fecha_inicio
            ff = fecha_fin
            fi_hora = '00:00:00'
            ff_hora = '23:59:59'

            if tipo_descarga == 'anio_completo':
                fi = f'{anio_clean}-01-01'
                ff = f'{anio_clean}-12-31'
            elif tipo_descarga == 'mes_especifico':
                fi = f'{anio_clean}-{mes_clean}-01'
                ff = _last_day_of_month(int(anio_clean), int(mes_clean))
            elif tipo_descarga != 'rango_personalizado':
                if not fi or not ff:
                    fi = f'{anio_clean}-01-01'
                    ff = f'{anio_clean}-12-31'
            else:
                fi, fi_hora = _normalize_custom_datetime(fi, '00:00:00')
                ff, ff_hora = _normalize_custom_datetime(ff, '23:59:59')

            if not fi or not ff:
                fi = f'{anio_clean}-01-01'
                ff = f'{anio_clean}-12-31'
                fi_hora = '00:00:00'
                ff_hora = '23:59:59'

            if tipo_descarga == 'rango_personalizado':
                try:
                    dt_inicio = datetime.strptime(f'{fi} {fi_hora}', '%Y-%m-%d %H:%M:%S')
                    dt_fin = datetime.strptime(f'{ff} {ff_hora}', '%Y-%m-%d %H:%M:%S')
                    if dt_fin < dt_inicio:
                        yield _send_event('error', {
                            'message': 'La fecha fin debe ser mayor o igual a la fecha inicio.',
                        })
                        return

                    max_fecha_fin = _add_one_calendar_year(dt_inicio)
                    if dt_fin > max_fecha_fin:
                        yield _send_event('error', {
                            'message': 'El rango personalizado no puede ser mayor a 1 año calendario.',
                        })
                        return
                except Exception:
                    yield _send_event('error', {
                        'message': 'Formato de fecha inválido en rango personalizado.',
                    })
                    return

            # Cap fecha_fin to yesterday (SAT rejects today)
            sat_today = _get_sat_today()
            max_cfdi_fecha_fin = (sat_today - timedelta(days=1)).strftime('%Y-%m-%d')
            if ff > max_cfdi_fecha_fin:
                ff = max_cfdi_fecha_fin
            if ff < fi:
                fi = ff

            # Load FIEL config
            fiel_config_path = os.path.join(BASE_DIR, 'config', 'fiel_config.json')
            if not os.path.isfile(fiel_config_path):
                yield _send_event('error', {
                    'message': 'No hay configuracion de FIEL. Configurala primero.',
                })
                return

            with open(fiel_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            cert_path = config_data.get('certificate_path', '')
            key_path = config_data.get('key_path', '')

            if not cert_path or not key_path:
                yield _send_event('error', {
                    'message': 'Configuracion de FIEL incompleta',
                })
                return

            if not os.path.isfile(cert_path) or not os.path.isfile(key_path):
                yield _send_event('error', {
                    'message': 'Archivos FIEL no encontrados',
                })
                return

            yield _send_event('progress', {
                'percent': 10,
                'message': 'Credenciales localizadas',
            })

            # Create FIEL and service
            try:
                with open(cert_path, 'rb') as f:
                    cert_contents = f.read()
                with open(key_path, 'rb') as f:
                    key_contents = f.read()

                fiel = Fiel.create(cert_contents, key_contents, fiel_password)
            except Exception as e:
                yield _send_event('error', {
                    'message': f'Error al crear la FIEL: {e}',
                })
                return

            if not fiel.is_valid():
                yield _send_event('error', {
                    'message': 'La FIEL no es valida o ya expiro',
                })
                return

            rfc = fiel.get_rfc()
            logger.info('[%s] FIEL validada correctamente', rfc)

            web_client = HttpxWebClient()
            request_builder = FielRequestBuilder(fiel)
            service_cfdi = Service(
                request_builder, web_client, None, ServiceEndpoints.cfdi()
            )

            yield _send_event('progress', {
                'percent': 15,
                'message': 'Conectado al SAT',
            })

            # Compute periodo folder
            if tipo_descarga == 'mes_especifico':
                periodo_folder = f'{anio_clean}-{mes_clean}'
            elif tipo_descarga == 'anio_completo':
                periodo_folder = anio_clean
            else:
                periodo_folder = (
                    fi.replace('-', '') + '_' + ff.replace('-', '')
                )

            download_base = os.path.join(BASE_DIR, 'descargas', periodo_folder)

            logger.info('[%s] Inicio descarga: tipo=%s, periodo=%s al %s, '
                        'nomina=%s, retenciones=%s, ingresos=%s, turbo=%s',
                        rfc, tipo_descarga, fi, ff,
                        want_nomina, want_retenciones, want_ingresos, want_turbo)

            _append_download_log(rfc, {
                'event': 'start',
                'tipo_descarga': tipo_descarga,
                'document_status': document_status,
                'fecha_inicio': fi,
                'fecha_fin': ff,
                'doc_nomina': want_nomina,
                'doc_retenciones': want_retenciones,
                'doc_ingresos': want_ingresos,
                'pretty_xml': want_pretty,
                'turbo_mode': want_turbo,
                'periodo_folder': periodo_folder,
            })

            summary: Dict = {
                'nominas': 0,
                'retenciones': 0,
                'ingresos': 0,
                'peticiones_realizadas': 0,
                'total_reintentos': 0,
            }
            current_progress = 15

            # ---------------------------------------------------------------
            # NOMINAS
            # ---------------------------------------------------------------
            if want_nomina:
                yield _send_event('progress', {
                    'percent': current_progress + 5,
                    'message': 'Procesando nominas...',
                })
                current_progress += 5

                nomina_fecha_fin_ext = _shift_date_by_days(ff, 45)
                max_nomina_fin = (sat_today - timedelta(days=1)).strftime('%Y-%m-%d')
                if nomina_fecha_fin_ext > max_nomina_fin:
                    nomina_fecha_fin_ext = max_nomina_fin
                if nomina_fecha_fin_ext < fi:
                    nomina_fecha_fin_ext = fi

                nomina_chunks = _split_date_range(
                    fi, nomina_fecha_fin_ext, SAT_MAX_QUERY_DAYS
                )
                nomina_total = 0

                if want_turbo and len(nomina_chunks) > 1:
                    turbo_ctx: Dict = {}
                    async for ev in _download_chunks_turbo(
                        service_cfdi,
                        nomina_chunks,
                        DocumentType.nomina(),
                        download_base,
                        'RECIBOS_DE_NOMINA',
                        document_status,
                        rfc,
                        0,
                        want_pretty,
                        'Nomina',
                        current_progress,
                        base_hora_inicio=fi_hora,
                        base_hora_fin=ff_hora,
                        ctx=turbo_ctx,
                    ):
                        yield ev
                    nomina_total += turbo_ctx.get('archivos', 0)
                    summary['peticiones_realizadas'] += turbo_ctx.get('peticiones_realizadas', 0)
                    summary['total_reintentos'] += turbo_ctx.get('reintentos', 0)
                    current_progress = turbo_ctx.get('progress', current_progress)
                else:
                    for idx, chunk in enumerate(nomina_chunks):
                        yield _send_event('progress', {
                            'percent': min(current_progress + 1, 95),
                            'message': (
                                f'Nomina lote {idx + 1}/{len(nomina_chunks)} '
                                f'({chunk["inicio"]} -> {chunk["fin"]})'
                            ),
                        })
                        retry_ctx: Dict = {}
                        async for ev in _download_with_retry(
                            service_cfdi,
                            DocumentType.nomina(),
                            'RECIBOS_DE_NOMINA',
                            fi, ff,
                            document_status,
                            download_base,
                            rfc,
                            0,
                            want_pretty,
                            current_progress,
                            chunk['inicio'],
                            chunk['fin'],
                            fi_hora,
                            ff_hora,
                            ctx=retry_ctx,
                        ):
                            yield ev
                        nomina_total += retry_ctx.get('archivos', 0)
                        current_progress = retry_ctx.get('progress', current_progress)

                summary['nominas'] = nomina_total

                # Apply FechaPago filter if date was extended
                if nomina_fecha_fin_ext != ff:
                    nomina_dir = os.path.join(download_base, 'RECIBOS_DE_NOMINA')
                    nomina_filter_info = _filter_xml_files_by_fecha_pago(
                        nomina_dir, fi, ff
                    )
                    if nomina_filter_info.get('removed', 0) > 0:
                        summary['nominas'] = max(
                            0, summary['nominas'] - nomina_filter_info['removed']
                        )
                        summary['nominas_fuera_periodo_eliminadas'] = (
                            nomina_filter_info['removed']
                        )

            # ---------------------------------------------------------------
            # RETENCIONES
            # ---------------------------------------------------------------
            if want_retenciones:
                yield _send_event('progress', {
                    'percent': current_progress + 5,
                    'message': 'Procesando retenciones...',
                })
                current_progress += 5

                service_retenciones = Service(
                    request_builder, web_client, None,
                    ServiceEndpoints.retenciones(),
                )

                # Business rule: retention certs for a selected year
                # are queried in the following year
                ret_fecha_inicio = _shift_date_by_years(fi, 1)
                ret_fecha_fin = _shift_date_by_years(ff, 1)

                max_ret_fin = (sat_today - timedelta(days=1)).strftime('%Y-%m-%d')
                if ret_fecha_fin > max_ret_fin:
                    ret_fecha_fin = max_ret_fin

                # If start falls in the future, skip
                if ret_fecha_inicio > max_ret_fin:
                    summary['retenciones'] = 0
                    summary['retenciones_sin_periodo_disponible'] = True

                    yield _send_event('progress', {
                        'percent': min(current_progress + 1, 95),
                        'message': (
                            f'Retenciones omitidas: el periodo consultable '
                            f'inicia en {ret_fecha_inicio} y SAT solo permite '
                            f'hasta {max_ret_fin} por ahora.'
                        ),
                    })

                    _append_download_log(rfc, {
                        'event': 'retenciones_skipped_future_range',
                        'selected_inicio': fi,
                        'selected_fin': ff,
                        'query_inicio': ret_fecha_inicio,
                        'query_fin_cap': max_ret_fin,
                    })
                else:
                    yield _send_event('progress', {
                        'percent': min(current_progress + 1, 95),
                        'message': (
                            f'Retenciones (ejercicio siguiente): '
                            f'{ret_fecha_inicio} -> {ret_fecha_fin}'
                        ),
                    })

                    _append_download_log(rfc, {
                        'event': 'retenciones_shifted_range',
                        'selected_inicio': fi,
                        'selected_fin': ff,
                        'query_inicio': ret_fecha_inicio,
                        'query_fin': ret_fecha_fin,
                    })

                    ret_chunks = _split_date_range(
                        ret_fecha_inicio, ret_fecha_fin, SAT_MAX_QUERY_DAYS
                    )
                    ret_total = 0

                    if want_turbo and len(ret_chunks) > 1:
                        ret_turbo_ctx: Dict = {}
                        async for ev in _download_chunks_turbo(
                            service_retenciones,
                            ret_chunks,
                            None,
                            download_base,
                            'CONSTANCIAS_DE_RETENCIONES',
                            document_status,
                            rfc,
                            1,
                            want_pretty,
                            'Retenciones',
                            current_progress,
                            base_hora_inicio=fi_hora,
                            base_hora_fin=ff_hora,
                            ctx=ret_turbo_ctx,
                        ):
                            yield ev
                        ret_total += ret_turbo_ctx.get('archivos', 0)
                        summary['peticiones_realizadas'] += ret_turbo_ctx.get('peticiones_realizadas', 0)
                        summary['total_reintentos'] += ret_turbo_ctx.get('reintentos', 0)
                        current_progress = ret_turbo_ctx.get('progress', current_progress)
                    else:
                        for idx, chunk in enumerate(ret_chunks):
                            yield _send_event('progress', {
                                'percent': min(current_progress + 1, 95),
                                'message': (
                                    f'Retenciones lote {idx + 1}/{len(ret_chunks)} '
                                    f'({chunk["inicio"]} -> {chunk["fin"]})'
                                ),
                            })
                            ret_retry_ctx: Dict = {}
                            async for ev in _download_with_retry(
                                service_retenciones,
                                None,
                                'CONSTANCIAS_DE_RETENCIONES',
                                fi, ff,
                                document_status,
                                download_base,
                                rfc,
                                1,
                                want_pretty,
                                current_progress,
                                chunk['inicio'],
                                chunk['fin'],
                                fi_hora,
                                ff_hora,
                                ctx=ret_retry_ctx,
                            ):
                                yield ev
                            ret_total += ret_retry_ctx.get('archivos', 0)
                            current_progress = ret_retry_ctx.get('progress', current_progress)

                    summary['retenciones'] = ret_total

            # ---------------------------------------------------------------
            # INGRESOS (otros CFDI)
            # ---------------------------------------------------------------
            if want_ingresos:
                yield _send_event('progress', {
                    'percent': current_progress + 5,
                    'message': 'Procesando otros CFDIs...',
                })
                current_progress += 5

                ingresos_chunks = _split_date_range(fi, ff, SAT_MAX_QUERY_DAYS)
                ingresos_total = 0

                if want_turbo and len(ingresos_chunks) > 1:
                    ing_turbo_ctx: Dict = {}
                    async for ev in _download_chunks_turbo(
                        service_cfdi,
                        ingresos_chunks,
                        DocumentType.ingreso(),
                        download_base,
                        'OTROS_CFDI',
                        document_status,
                        rfc,
                        0,
                        want_pretty,
                        'Ingresos',
                        current_progress,
                        base_hora_inicio=fi_hora,
                        base_hora_fin=ff_hora,
                        ctx=ing_turbo_ctx,
                    ):
                        yield ev
                    ingresos_total += ing_turbo_ctx.get('archivos', 0)
                    summary['peticiones_realizadas'] += ing_turbo_ctx.get('peticiones_realizadas', 0)
                    summary['total_reintentos'] += ing_turbo_ctx.get('reintentos', 0)
                    current_progress = ing_turbo_ctx.get('progress', current_progress)
                else:
                    for idx, chunk in enumerate(ingresos_chunks):
                        yield _send_event('progress', {
                            'percent': min(current_progress + 1, 95),
                            'message': (
                                f'Ingresos lote {idx + 1}/{len(ingresos_chunks)} '
                                f'({chunk["inicio"]} -> {chunk["fin"]})'
                            ),
                        })
                        ing_retry_ctx: Dict = {}
                        async for ev in _download_with_retry(
                            service_cfdi,
                            DocumentType.ingreso(),
                            'OTROS_CFDI',
                            fi, ff,
                            document_status,
                            download_base,
                            rfc,
                            0,
                            want_pretty,
                            current_progress,
                            chunk['inicio'],
                            chunk['fin'],
                            fi_hora,
                            ff_hora,
                            ctx=ing_retry_ctx,
                        ):
                            yield ev
                        ingresos_total += ing_retry_ctx.get('archivos', 0)
                        current_progress = ing_retry_ctx.get('progress', current_progress)

                summary['ingresos'] = ingresos_total

            # ---------------------------------------------------------------
            # FechaPago global filter
            # ---------------------------------------------------------------
            total_archivos = (
                summary.get('nominas', 0)
                + summary.get('retenciones', 0)
                + summary.get('ingresos', 0)
            )

            fecha_pago_filter_info: Dict = {'evaluated': 0, 'removed': 0}
            if want_filter:
                yield _send_event('progress', {
                    'percent': min(current_progress + 2, 98),
                    'message': 'Aplicando filtro por FechaPago...',
                })
                fecha_pago_filter_info = _filter_xml_files_by_fecha_pago(
                    download_base, fi, ff
                )
                summary['filtrados_fecha_pago'] = fecha_pago_filter_info['removed']
                total_archivos = max(
                    0, total_archivos - fecha_pago_filter_info['removed']
                )
                yield _send_event('progress', {
                    'percent': min(current_progress + 4, 99),
                    'message': (
                        f'Evaluados {fecha_pago_filter_info["evaluated"]} CFDI | '
                        f'Removidos {fecha_pago_filter_info["removed"]} por FechaPago'
                    ),
                })

            # ---------------------------------------------------------------
            # Success
            # ---------------------------------------------------------------
            logger.info('[%s] Descarga completada: %d archivos '
                        '(nominas=%d, retenciones=%d, ingresos=%d)',
                        rfc, total_archivos,
                        summary.get('nominas', 0),
                        summary.get('retenciones', 0),
                        summary.get('ingresos', 0))

            yield _send_event('success', {
                'percent': 100,
                'message': 'Descarga completada',
                'success': True,
                'summary': summary,
                'output_dir': (
                    '/api/downloads/browse?folder=' + quote(periodo_folder, safe='')
                ),
                'periodo': f'{fi} al {ff}',
                'total_archivos': total_archivos,
                'peticiones_realizadas': summary['peticiones_realizadas'],
                'total_reintentos': summary['total_reintentos'],
                'fecha_pago_filter': fecha_pago_filter_info,
            })

        except Exception as e:
            logger.error('Error en sat/download/stream: %s', e, exc_info=True)
            yield _send_event('error', {
                'message': str(e),
            })

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )
