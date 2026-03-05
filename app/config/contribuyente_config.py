"""
Manages taxpayer (contribuyente) data configuration.
"""

import json
import os
import re
from typing import Optional

# Project root: two levels up from this file (app/config/contribuyente_config.py -> project root)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'contribuyente_data.json')


class ContribuyenteConfig:
    """Static methods for taxpayer data management."""

    # --- Validators -----------------------------------------------------------

    @staticmethod
    def validate_rfc(rfc: str) -> dict:
        """Validate RFC format."""
        rfc = (rfc or '').strip().upper()

        if not rfc:
            return {'valid': False, 'message': 'El RFC es requerido'}

        pattern = r'^[A-Z\u00d1&]{3,4}\d{6}[A-Z0-9]{3}$'
        if not re.match(pattern, rfc):
            return {
                'valid': False,
                'message': (
                    'El RFC debe tener el formato correcto: '
                    '3-4 letras, 6 digitos (AAMMDD), 3 caracteres finales'
                ),
            }

        return {'valid': True, 'rfc': rfc}

    @staticmethod
    def validate_curp(curp: str) -> dict:
        """Validate CURP format."""
        curp = (curp or '').strip().upper()

        if not curp:
            return {'valid': False, 'message': 'El CURP es requerido'}

        pattern = r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$'
        if not re.match(pattern, curp):
            return {
                'valid': False,
                'message': 'El CURP debe tener 18 caracteres con el formato correcto',
            }

        return {'valid': True, 'curp': curp}

    # --- Persistence ----------------------------------------------------------

    @staticmethod
    def save_data(data: dict) -> dict:
        """
        Validate and save taxpayer data to ``config/contribuyente_data.json``.

        Expected keys in *data*: ``nombre``, ``rfc``, ``curp``.
        """
        try:
            # Validate nombre
            nombre = (data.get('nombre') or '').strip()
            if not nombre:
                return {'success': False, 'message': 'El nombre es requerido'}

            # Validate RFC
            rfc_result = ContribuyenteConfig.validate_rfc(data.get('rfc', ''))
            if not rfc_result['valid']:
                return {'success': False, 'message': rfc_result['message']}

            # Validate CURP
            curp_result = ContribuyenteConfig.validate_curp(data.get('curp', ''))
            if not curp_result['valid']:
                return {'success': False, 'message': curp_result['message']}

            clean_data = {
                'nombre': nombre,
                'rfc': rfc_result['rfc'],
                'curp': curp_result['curp'],
            }

            # Ensure config directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=4, ensure_ascii=False)

            return {
                'success': True,
                'message': 'Tus datos fiscales se guardaron correctamente',
                'data': clean_data,
            }

        except Exception as e:
            return {'success': False, 'message': f'Error al guardar: {e}'}

    @staticmethod
    def load_data() -> dict:
        """
        Load taxpayer data from ``config/contribuyente_data.json``.
        Returns a dict with ``has_data`` flag.
        """
        if not os.path.isfile(CONFIG_FILE):
            return {'has_data': False}

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not data:
                return {'has_data': False}

            return {
                'has_data': True,
                'nombre': data.get('nombre', ''),
                'rfc': data.get('rfc', ''),
                'curp': data.get('curp', ''),
            }

        except Exception as e:
            return {'has_data': False, 'error': str(e)}

    @staticmethod
    def has_data() -> bool:
        """Check whether a saved configuration file exists."""
        return os.path.isfile(CONFIG_FILE)
