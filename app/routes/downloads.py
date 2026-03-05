"""
Downloads file-browser routes.
"""

import os
import re
import subprocess
import sys
from html import escape
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
DESCARGAS_DIR = os.path.join(BASE_DIR, 'descargas')

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


@router.get("/status")
async def check_downloads():
    """Check whether there are any downloaded files."""
    response = {
        'success': True,
        'has_downloads': False,
        'viewer_url': '/api/downloads/browse',
    }

    real_base = os.path.realpath(DESCARGAS_DIR)
    if not os.path.isdir(real_base):
        return response

    try:
        has_any_file = False

        for dirpath, _dirnames, filenames in os.walk(real_base):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    os.path.getmtime(filepath)
                except OSError:
                    continue
                has_any_file = True
                break
            if has_any_file:
                break

        if has_any_file:
            response['has_downloads'] = True
    except Exception as e:
        response['success'] = False
        response['error'] = str(e)

    return response


@router.get("/browse", response_class=HTMLResponse)
async def browse_downloads(folder: Optional[str] = Query(None)):
    """HTML file-browser for the descargas/ directory."""
    real_base = os.path.realpath(DESCARGAS_DIR)
    if not os.path.isdir(real_base):
        return HTMLResponse(
            content='No se encontro la carpeta de descargas.',
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
        display_folder = 'descargas'
    else:
        display_folder = 'descargas/' + relative_folder.replace(os.sep, '/')

    try:
        entries = sorted(
            [e for e in os.listdir(target_path) if e not in ('.', '..')],
        )
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
                    <th>Tamano</th>
                    <th>Accion</th>
                </tr>
            </thead>
            <tbody>'''
        for entry in entries:
            entry_path = os.path.join(target_path, entry)
            is_dir = os.path.isdir(entry_path)
            safe_name = escape(entry)
            next_folder = (clean_folder + '/' + entry).lstrip('/')

            if is_dir:
                action = (
                    f'<a href="/api/downloads/browse?folder='
                    f'{quote(next_folder, safe="")}">Abrir</a>'
                )
                size = '---'
                badge = 'Carpeta'
            else:
                action = (
                    f'<a href="/api/downloads/open-folder?folder={quote(clean_folder, safe="")}'
                    f'&file={quote(entry, safe="")}">Abrir ubicación</a>'
                )
                try:
                    size = _human_size(os.path.getsize(entry_path))
                except OSError:
                    size = '---'
                badge = 'Archivo'

            rows_html += f'''
                <tr>
                    <td>{safe_name}</td>
                    <td><span class="badge">{badge}</span></td>
                    <td>{size}</td>
                    <td>{action}</td>
                </tr>'''

        rows_html += '</tbody></table>'

    back_link = ''
    if clean_folder:
        back_link = '<a href="/api/downloads/browse">&#8592; Volver a la carpeta inicial</a>'

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Archivos descargados - SAT</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background: #111827; color: #e5e7eb; }}
        h1 {{ margin-bottom: 5px; }}
        .breadcrumb {{ font-size: 0.9em; margin-bottom: 20px; color: #94a3b8; }}
        table {{ width: 100%; border-collapse: collapse; background: #1f2937; box-shadow: 0 2px 8px rgba(0,0,0,0.35); }}
        th, td {{ padding: 10px 12px; border-bottom: 1px solid #334155; }}
        th {{ background: #0d6efd; color: white; text-align: left; }}
        tr:hover {{ background: #273449; }}
        a {{ color: #0d6efd; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; background: #334155; color: #e2e8f0; }}
        .empty {{ padding: 30px; text-align: center; color: #94a3b8; }}
        .toolbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .btn-back {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; background: #198754; color: #fff; border-radius: 6px; text-decoration: none; font-weight: 600; }}
        .btn-back:hover {{ background: #157347; }}
    </style>
</head>
<body>
    <h1>Archivos descargados</h1>
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
async def open_downloads_folder(
    folder: Optional[str] = Query(None),
    file: Optional[str] = Query(None),
):
    """Open descargas/ (or a subfolder) in the OS file explorer.
    When 'file' is provided, tries to select it in the explorer.
    """
    real_base = os.path.realpath(DESCARGAS_DIR)
    if not os.path.isdir(real_base):
        return HTMLResponse(
            content='No se encontro la carpeta de descargas.',
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

    redirect_url = '/api/downloads/browse'
    if clean_folder:
        redirect_url += f'?folder={quote(clean_folder, safe="")}'

    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/file")
async def download_file(
    folder: str = Query(''),
    download: str = Query(''),
    type: str = Query('descargas'),
):
    """Serve a file for download from descargas/ or reportes/ or storage/reporting-logs/.
    """
    allowed_types = ('descargas', 'report', 'log')
    if type not in allowed_types:
        return JSONResponse(content='Tipo invalido.', status_code=400)

    if type == 'log':
        base = os.path.realpath(os.path.join(BASE_DIR, 'storage', 'reporting-logs'))
    elif type == 'report':
        base = os.path.realpath(os.path.join(BASE_DIR, 'reportes'))
    else:
        # type == 'descargas'
        clean_folder = (folder or '').strip('/\\')
        if clean_folder and '..' in clean_folder:
            return JSONResponse(content='Parametro invalido.', status_code=400)
        base = os.path.realpath(DESCARGAS_DIR)
        if clean_folder:
            base = os.path.realpath(os.path.join(base, clean_folder))

    if not os.path.isdir(base):
        return JSONResponse(content='Directorio base no disponible.', status_code=500)

    file_param = download.strip('/\\')
    if not file_param or '..' in file_param:
        return JSONResponse(content='Archivo requerido.', status_code=400)

    target = os.path.realpath(os.path.join(base, file_param))

    real_base = os.path.realpath(base)
    if (
        not os.path.isfile(target)
        or not target.startswith(real_base)
    ):
        return JSONResponse(content='Archivo no encontrado.', status_code=404)

    filename = os.path.basename(target)

    if type == 'log':
        media_type = 'text/plain; charset=UTF-8'
    elif type == 'report':
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        media_type = 'application/octet-stream'

    return FileResponse(
        path=target,
        filename=filename,
        media_type=media_type,
    )
