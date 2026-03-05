"""
Bootstrap helpers for local runtime files.
"""

import json
import os

# Project root: two levels up from this file (app/config/bootstrap.py -> project root)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _ensure_json_file(path: str, payload: dict) -> None:
    if os.path.isfile(path):
        return
    _ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def ensure_local_runtime_files() -> None:
    """
    Ensure local folders and config JSON files exist.

    Files are intentionally created with empty/minimal values so users can
    complete them from the web UI.
    """
    _ensure_dir(os.path.join(BASE_DIR, 'config'))
    _ensure_dir(os.path.join(BASE_DIR, 'fiel-uploads'))
    _ensure_dir(os.path.join(BASE_DIR, 'descargas'))
    _ensure_dir(os.path.join(BASE_DIR, 'reportes'))
    _ensure_dir(os.path.join(BASE_DIR, 'storage'))
    _ensure_dir(os.path.join(BASE_DIR, 'storage', 'download-logs'))
    _ensure_dir(os.path.join(BASE_DIR, 'storage', 'reporting-logs'))
    _ensure_dir(os.path.join(BASE_DIR, 'storage', 'reporting-smoke'))
    _ensure_dir(os.path.join(BASE_DIR, 'storage', 'tabuladores'))

    _ensure_json_file(os.path.join(BASE_DIR, 'config', 'fiel_config.json'), {})
    _ensure_json_file(os.path.join(BASE_DIR, 'config', 'contribuyente_data.json'), {})
    _ensure_json_file(os.path.join(BASE_DIR, 'config', 'tabulador_isr.json'), {'periods': {}})
