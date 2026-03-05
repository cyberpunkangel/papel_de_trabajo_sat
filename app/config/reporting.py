"""
Reporting configuration: paths for the report-generation pipeline.
"""

import os
import sys

# Project root: two levels up from this file (app/config/reporting.py -> project root)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def get_reporting_config() -> dict:
    """
    Return a dict with all paths needed by the reporting subsystem.

    Python path detection order:
    1. ``REPORTING_PYTHON`` environment variable
    2. Virtual-env inside the project root (``.venv``)
    3. Virtual-env one level above the project root (workspace root)
    4. Fallback to ``python``
    """
    workspace_root = os.path.normpath(os.path.join(BASE_DIR, '..'))

    venv_candidates = []

    # Project-level venv
    if sys.platform == 'win32':
        venv_candidates.append(os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe'))
    else:
        venv_candidates.append(os.path.join(BASE_DIR, '.venv', 'bin', 'python'))

    # Also check the other platform variant within the project
    if sys.platform == 'win32':
        venv_candidates.append(os.path.join(BASE_DIR, '.venv', 'bin', 'python'))
    else:
        venv_candidates.append(os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe'))

    # Workspace-level venv (one directory up)
    if os.path.normpath(workspace_root) != os.path.normpath(BASE_DIR):
        if sys.platform == 'win32':
            venv_candidates.append(
                os.path.join(workspace_root, '.venv', 'Scripts', 'python.exe')
            )
            venv_candidates.append(
                os.path.join(workspace_root, '.venv', 'bin', 'python')
            )
        else:
            venv_candidates.append(
                os.path.join(workspace_root, '.venv', 'bin', 'python')
            )
            venv_candidates.append(
                os.path.join(workspace_root, '.venv', 'Scripts', 'python.exe')
            )

    venv_python = None
    for candidate in venv_candidates:
        if os.path.isfile(candidate):
            venv_python = os.path.realpath(candidate)
            break

    python_path = os.environ.get('REPORTING_PYTHON') or venv_python or 'python'

    return {
        'python_path': python_path,
        'script_path': os.path.join(BASE_DIR, 'reporting', 'generate_report.py'),
        'descargas_dir': os.path.join(BASE_DIR, 'descargas'),
        'output_dir': os.path.join(BASE_DIR, 'reportes'),
        'logs_dir': os.path.join(BASE_DIR, 'storage', 'reporting-logs'),
        'config_file': os.path.join(BASE_DIR, 'config', 'contribuyente_data.json'),
    }
