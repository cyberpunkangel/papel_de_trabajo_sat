"""
Reports generation and browsing routes.
"""

import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime
from html import escape
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config.contribuyente_config import ContribuyenteConfig
from app.config.reporting import get_reporting_config
from app.config.tabulador_config import TabuladorConfig, DEFAULT_PERIOD_KEY

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
REPORTES_DIR = os.path.join(BASE_DIR, 'reportes')

router = APIRouter()


def _human_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    val = float(size_bytes)
    idx = 0
    while val >= 1024 and idx < len(units) - 1:
        val /= 1024
        idx += 1
    return f'{val:.2f} {units[idx]}'


def _format_timestamp(path: str) -> str:
    """Return a dd/mm/YYYY HH:MM string from a file's mtime."""
    try:
        mtime = os.path.getmtime(path)
        dt_obj = datetime.fromtimestamp(mtime)
        return dt_obj.strftime('%d/%m/%Y %H:%M')
    except OSError:
        return '---'


def _normalize_period_input(value: Optional[str]) -> str:
    """Normalize a period input to a 4-digit year or empty string."""
    trimmed = (value or '').strip()
    if not trimmed:
        return ''
    if trimmed == DEFAULT_PERIOD_KEY:
        return DEFAULT_PERIOD_KEY
    digits = re.sub(r'[^0-9]', '', trimmed)
    return digits if len(digits) == 4 else ''


def _build_download_url(file_path: str, file_type: str) -> Optional[str]:
    """Build a download URL relative to the download/file endpoint."""
    if file_type == 'log':
        base = os.path.realpath(os.path.join(BASE_DIR, 'storage', 'reporting-logs'))
    else:
        base = os.path.realpath(REPORTES_DIR)

    if not base or not os.path.isdir(base):
        return None

    real_path = os.path.realpath(file_path)
    if not real_path.startswith(base):
        return None

    relative = os.path.relpath(real_path, base).replace(os.sep, '/')
    return (
        f'/api/downloads/file?type={quote(file_type, safe="")}'
        f'&download={quote(relative, safe="")}'
    )


def _write_temporary_tabulador(normalized: list) -> str:
    """Write a temporary tabulador JSON file and return the file path."""
    if not normalized:
        raise ValueError(
            'El tabulador ISR debe contener al menos una fila completa.',
        )

    storage_dir = os.path.join(BASE_DIR, 'storage')
    tabulador_dir = os.path.join(storage_dir, 'tabuladores')
    os.makedirs(tabulador_dir, exist_ok=True)

    random_hex = secrets.token_hex(4)
    filename = f'tabulador_isr_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{random_hex}.json'
    target_path = os.path.join(tabulador_dir, filename)

    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=4, ensure_ascii=False)

    return target_path


@router.get("/status")
async def check_report_status():
    """Check if there are generated report files."""
    viewer_url = '/api/reports/browse'
    real_base = os.path.realpath(REPORTES_DIR)

    if not os.path.isdir(real_base):
        return {'success': True, 'has_report': False, 'viewer_url': viewer_url}

    import glob as globmod
    xlsx_files = globmod.glob(os.path.join(real_base, '*.xlsx'))
    if not xlsx_files:
        return {'success': True, 'has_report': False, 'viewer_url': viewer_url}

    # Sort by modification time descending
    xlsx_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    latest = xlsx_files[0]

    relative = os.path.relpath(latest, real_base).replace(os.sep, '/')
    generated_at = os.path.getmtime(latest)
    dt_obj = datetime.fromtimestamp(generated_at)

    return {
        'success': True,
        'has_report': True,
        'viewer_url': viewer_url,
        'report': {
            'filename': os.path.basename(latest),
            'download_url': (
                f'/api/downloads/file?type=report&download='
                f'{quote(relative, safe="")}'
            ),
            'viewer_url': viewer_url,
            'generated_at': dt_obj.isoformat(),
            'generated_display': dt_obj.strftime('%d/%m/%Y %H:%M'),
            'size': os.path.getsize(latest),
        },
    }


@router.post("/generate")
async def generate_report(
    periodo: str = Form(''),
    tabulador_isr: str = Form(''),
    tabulador_periodo: str = Form(''),
):
    """Generate the workpaper report via subprocess."""
    reporting = get_reporting_config()

    if not ContribuyenteConfig.has_data():
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'message': 'Primero guarda tus datos fiscales en "Datos del Contribuyente".',
            },
        )

    python_path = reporting.get('python_path', 'python')
    script_path = reporting.get('script_path')

    if not script_path or not os.path.isfile(script_path):
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': 'No se encontro el script de generacion.',
            },
        )

    requested_period = re.sub(r'[^0-9]', '', periodo or '')
    if len(requested_period) != 4:
        requested_period = ''

    tab_period = (
        _normalize_period_input(tabulador_periodo or periodo) or requested_period
    )

    tabulador_file: Optional[str] = None
    normalized_tabulador: list = []

    try:
        raw_tab = (tabulador_isr or '').strip()
        if raw_tab:
            if not tab_period or tab_period == DEFAULT_PERIOD_KEY:
                raise ValueError(
                    'Selecciona un ejercicio valido (4 digitos) para guardar '
                    'el tabulador ISR.',
                )
            normalized_tabulador = TabuladorConfig.normalize_payload(raw_tab)
            TabuladorConfig.save_normalized(normalized_tabulador, tab_period)
        else:
            if not tab_period:
                raise ValueError(
                    'Selecciona el ejercicio del tabulador ISR que deseas utilizar.',
                )
            stored = TabuladorConfig.load_data(tab_period)
            if not stored.get('has_data') or not stored.get('rows'):
                raise ValueError(
                    f'No se encontro un tabulador ISR guardado para el ejercicio {tab_period}.',
                )
            normalized_tabulador = stored['rows']

        tabulador_file = _write_temporary_tabulador(normalized_tabulador)

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': str(e)},
        )
    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'message': str(e)},
        )

    # Build command arguments
    arguments = {
        '--descargas-dir': reporting.get('descargas_dir'),
        '--output-dir': reporting.get('output_dir'),
        '--logs-dir': reporting.get('logs_dir'),
        '--config-file': reporting.get('config_file'),
        '--periodo': requested_period or None,
        '--tabulador-isr': tabulador_file,
    }

    cmd = [python_path, script_path]
    for flag, value in arguments.items():
        if value:
            cmd.extend([flag, value])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=300,
        )

        output_text = (result.stdout or '').strip() or (result.stderr or '').strip()
        try:
            response_data = json.loads(output_text)
        except (json.JSONDecodeError, TypeError):
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'message': 'No se pudo interpretar la respuesta del generador.',
                    'details': result.stderr or '',
                },
            )

        if not isinstance(response_data, dict):
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'message': 'No se pudo interpretar la respuesta del generador.',
                },
            )

        if not response_data.get('success') or result.returncode != 0:
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'message': response_data.get(
                        'message', 'El generador reporto un error.'
                    ),
                    'log_file': response_data.get('log_file'),
                },
            )

        download_url = None
        if response_data.get('output_file'):
            download_url = _build_download_url(
                response_data['output_file'], 'report'
            )

        log_url = None
        if response_data.get('log_file'):
            log_url = _build_download_url(response_data['log_file'], 'log')

        return {
            'success': True,
            'message': response_data.get(
                'message', 'Papel de trabajo generado correctamente.'
            ),
            'report_url': download_url,
            'log_url': log_url,
            'periodo': response_data.get('periodo'),
            'tabulador_periodo': tab_period,
            'stats': response_data.get('stats', {}),
            'viewer_url': '/api/reports/browse',
        }

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': 'El proceso de generacion excedio el tiempo limite.',
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f'No se pudo iniciar el proceso de generacion: {e}',
            },
        )
    finally:
        if tabulador_file and os.path.isfile(tabulador_file):
            try:
                os.unlink(tabulador_file)
            except OSError:
                pass


@router.get("/browse", response_class=HTMLResponse)
async def browse_reports(folder: Optional[str] = Query(None)):
    """HTML file-browser for the reportes/ directory."""
    real_base = os.path.realpath(REPORTES_DIR)
    if not os.path.isdir(real_base):
        return HTMLResponse(
            content='No se encontro la carpeta de papeles de trabajo.',
            status_code=500,
        )

    clean_folder = (folder or '').strip('/\\')
    if clean_folder == '.':
        clean_folder = ''

    if clean_folder and not re.match(r'^[A-Za-z0-9_\-/]+$', clean_folder):
        return HTMLResponse(content='Parametro invalido.', status_code=400)

    if clean_folder:
        target_path = os.path.realpath(os.path.join(real_base, clean_folder))
    else:
        target_path = real_base

    if (
        not os.path.isdir(target_path)
        or not target_path.startswith(real_base)
    ):
        return HTMLResponse(content='Directorio no encontrado.', status_code=404)

    relative_folder = os.path.relpath(target_path, real_base)
    if relative_folder == '.':
        display_folder = 'reportes'
    else:
        display_folder = 'reportes/' + relative_folder.replace(os.sep, '/')

    try:
        entries = sorted([
            e for e in os.listdir(target_path)
            if e not in ('.', '..') and not e.startswith('~$')
        ])
    except OSError:
        entries = []

    rows_html = ''
    if not entries:
        rows_html = '<div class="empty">No hay archivos en esta carpeta.</div>'
    else:
        rows_html = '''<table>
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Ultima modificacion</th>
                    <th>Tamano</th>
                    <th>Accion</th>
                </tr>
            </thead>
            <tbody>'''

        for entry in entries:
            entry_path = os.path.join(target_path, entry)
            is_dir = os.path.isdir(entry_path)
            safe_name = escape(entry)
            next_folder = ((clean_folder + '/' if clean_folder else '') + entry).lstrip('/')

            if is_dir:
                action = (
                    f'<a href="/api/reports/browse?folder='
                    f'{quote(next_folder, safe="")}">Abrir</a>'
                )
                size = '---'
                mtime_display = '---'
                badge = 'Carpeta'
            else:
                # Build open-location URL for report file
                relative = next_folder.replace(os.sep, '/')
                action = (
                    f'<div class="actions">'
                    f'<a href="/api/reports/open-folder?folder={quote(clean_folder, safe="")}'
                    f'&file={quote(entry, safe="")}">Abrir ubicación</a>'
                    f'</div>'
                )
                try:
                    size = _human_size(os.path.getsize(entry_path))
                except OSError:
                    size = '---'
                mtime_display = escape(_format_timestamp(entry_path))
                badge = 'Archivo'

            rows_html += f'''
                <tr>
                    <td>{safe_name}</td>
                    <td><span class="badge">{badge}</span></td>
                    <td>{"---" if is_dir else mtime_display}</td>
                    <td>{size}</td>
                    <td>{action}</td>
                </tr>'''

        rows_html += '</tbody></table>'

    back_link = ''
    if clean_folder:
        back_link = (
            '<a class="back-link" href="/api/reports/browse">'
            '&#8592; Volver a la carpeta inicial</a>'
        )

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Papeles de trabajo generados</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background: #111827; color: #e5e7eb; }}
        h1 {{ margin-bottom: 5px; }}
        .breadcrumb {{ font-size: 0.9em; margin-bottom: 20px; color: #94a3b8; }}
        table {{ width: 100%; border-collapse: collapse; background: #1f2937; box-shadow: 0 2px 8px rgba(0,0,0,0.35); }}
        th, td {{ padding: 10px 12px; border-bottom: 1px solid #334155; }}
        th {{ background: #198754; color: white; text-align: left; }}
        tr:hover {{ background: #273449; }}
        a {{ color: #198754; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; background: #334155; color: #e2e8f0; }}
        .empty {{ padding: 30px; text-align: center; color: #94a3b8; }}
        .actions {{ display: flex; gap: 8px; }}
        .back-link {{ margin-bottom: 15px; display: inline-block; }}
        .toolbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .btn-back {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; background: #0d6efd; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 600; }}
        .btn-back:hover {{ background: #0b5ed7; }}
    </style>
</head>
<body>
    <h1>Papeles de trabajo generados</h1>
    <p class="breadcrumb">Ubicacion actual: {escape(display_folder)}</p>
    <div class="toolbar">
        <a class="btn-back" href="/">&#8592; Regresar al panel</a>
        {back_link}
    </div>
    {rows_html}
</body>
</html>'''

    return HTMLResponse(content=html)


@router.get("/open-folder")
async def open_reports_folder(
    folder: Optional[str] = Query(None),
    file: Optional[str] = Query(None),
):
    """Open reportes/ (or a subfolder) in the OS file explorer.
    When 'file' is provided, tries to select it in the explorer.
    """
    real_base = os.path.realpath(REPORTES_DIR)
    if not os.path.isdir(real_base):
        return HTMLResponse(
            content='No se encontro la carpeta de papeles de trabajo.',
            status_code=500,
        )

    clean_folder = (folder or '').strip('/\\')
    if clean_folder == '.':
        clean_folder = ''

    if clean_folder and not re.match(r'^[A-Za-z0-9_\-/]+$', clean_folder):
        return HTMLResponse(content='Parametro invalido.', status_code=400)

    if clean_folder:
        target_path = os.path.realpath(os.path.join(real_base, clean_folder))
    else:
        target_path = real_base

    if (
        not os.path.isdir(target_path)
        or not target_path.startswith(real_base)
    ):
        return HTMLResponse(content='Directorio no encontrado.', status_code=404)

    selected_file_path: Optional[str] = None
    selected_file_name = (file or '').strip()
    if selected_file_name:
        if not re.match(r'^[A-Za-z0-9_.\- ]+$', selected_file_name):
            return HTMLResponse(content='Parametro de archivo invalido.', status_code=400)

        candidate = os.path.realpath(os.path.join(target_path, selected_file_name))
        if (
            not os.path.isfile(candidate)
            or not candidate.startswith(target_path)
        ):
            return HTMLResponse(content='Archivo no encontrado.', status_code=404)

        selected_file_path = candidate

    try:
        if os.name == 'nt':
            normalized_target_path = os.path.normpath(target_path)
            if selected_file_path:
                normalized_selected_path = os.path.normpath(selected_file_path)
                subprocess.Popen(
                    f'explorer.exe /select,"{normalized_selected_path}"',
                    shell=True,
                    cwd=normalized_target_path,
                )
            else:
                subprocess.Popen(
                    ['explorer.exe', normalized_target_path],
                    cwd=normalized_target_path,
                )
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', target_path])
        else:
            subprocess.Popen(['xdg-open', target_path])
    except Exception as exc:
        return HTMLResponse(
            content=f'No se pudo abrir la carpeta: {escape(str(exc))}',
            status_code=500,
        )

    redirect_url = '/api/reports/browse'
    if clean_folder:
        redirect_url += f'?folder={quote(clean_folder, safe="")}'

    return RedirectResponse(url=redirect_url, status_code=303)
