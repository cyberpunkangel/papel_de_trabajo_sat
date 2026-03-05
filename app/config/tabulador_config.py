"""
Manages ISR tax bracket (tabulador) configuration.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional, List

# Project root: two levels up from this file (app/config/tabulador_config.py -> project root)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'tabulador_isr.json')

DEFAULT_PERIOD_KEY = '__default__'


class TabuladorConfig:
    """Static methods for ISR tax bracket table management."""

    @staticmethod
    def get_config_path() -> str:
        return CONFIG_FILE

    # --- Public API -----------------------------------------------------------

    @staticmethod
    def has_data(period: Optional[str] = None) -> bool:
        data = TabuladorConfig.load_data(period)
        return bool(data.get('has_data')) and bool(data.get('rows'))

    @staticmethod
    def load_data(period: Optional[str] = None) -> dict:
        """
        Load tabulador data for a given *period*.

        Returns a dict with ``has_data``, ``period``, ``rows``,
        ``updated_at`` and ``available_periods``.
        """
        dataset = TabuladorConfig._read_config()
        periods = dataset['periods']
        available = TabuladorConfig._build_available_periods(periods)

        if not periods:
            return {
                'has_data': False,
                'period': None,
                'rows': [],
                'available_periods': available,
            }

        normalized_request = TabuladorConfig.normalize_period_key(period)
        target_period = (
            normalized_request
            if normalized_request != ''
            else TabuladorConfig._resolve_default_period(periods)
        )

        if target_period not in periods:
            return {
                'has_data': False,
                'period': target_period,
                'rows': [],
                'available_periods': available,
            }

        entry = periods[target_period]
        return {
            'has_data': True,
            'period': target_period,
            'rows': entry.get('rows', []),
            'updated_at': entry.get('updated_at'),
            'available_periods': available,
        }

    @staticmethod
    def save_from_payload(period: Optional[str], raw_payload: str) -> dict:
        """Normalize a raw JSON payload and save it under *period*."""
        period_key = TabuladorConfig.assert_savable_period(period)
        normalized = TabuladorConfig.normalize_payload(raw_payload)
        dataset = TabuladorConfig._store_period_rows(period_key, normalized)

        entry = dataset['periods'].get(period_key, {})
        return {
            'success': True,
            'period': period_key,
            'rows': normalized,
            'updated_at': entry.get('updated_at', datetime.now(timezone.utc).isoformat()),
            'available_periods': TabuladorConfig._build_available_periods(
                dataset['periods']
            ),
        }

    @staticmethod
    def normalize_payload(raw_payload: str) -> list:
        """Parse a JSON string and normalize its rows."""
        if not (raw_payload or '').strip():
            raise ValueError('Debes capturar el tabulador ISR.')

        try:
            decoded = json.loads(raw_payload)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(
                'El tabulador ISR recibido no tiene un formato valido.'
            )

        if not isinstance(decoded, list):
            raise ValueError(
                'El tabulador ISR recibido no tiene un formato valido.'
            )

        return TabuladorConfig.normalize_rows(decoded)

    @staticmethod
    def normalize_rows(rows: list) -> list:
        """Validate and normalize a list of bracket rows."""
        normalized: List[dict] = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            raw_upper = row.get('upper_limit')
            lower = TabuladorConfig._normalize_number(row.get('lower_limit'))
            upper = TabuladorConfig._normalize_number(raw_upper)
            fixed = TabuladorConfig._normalize_number(row.get('fixed_fee'))
            rate = TabuladorConfig._normalize_number(row.get('rate'), as_percent=True)

            if lower is None or fixed is None or rate is None:
                continue

            upper_value = upper
            if upper_value is None and raw_upper is not None:
                label = str(raw_upper).strip()
                upper_value = label if label else None

            normalized.append({
                'lower_limit': lower,
                'upper_limit': upper_value,
                'fixed_fee': fixed,
                'rate': rate,
            })

        if not normalized:
            raise ValueError(
                'El tabulador ISR debe contener al menos una fila completa.'
            )

        return normalized

    @staticmethod
    def save_normalized(normalized: list, period: Optional[str]) -> None:
        """Save already-normalised rows under *period*."""
        if not normalized:
            raise ValueError(
                'El tabulador ISR debe contener al menos una fila completa.'
            )

        period_key = TabuladorConfig.assert_savable_period(period)
        TabuladorConfig._store_period_rows(period_key, normalized)

    @staticmethod
    def normalize_period_key(period: Optional[str]) -> str:
        """
        Return a normalised period key.

        A valid key is either the special period key or a four-digit year string.
        Returns an empty string when the input cannot be normalised.
        """
        value = (period or '').strip()
        if not value:
            return ''
        if value == DEFAULT_PERIOD_KEY:
            return DEFAULT_PERIOD_KEY

        digits = re.sub(r'[^0-9]', '', value)
        return digits if len(digits) == 4 else ''

    @staticmethod
    def assert_savable_period(period: Optional[str]) -> str:
        """
        Return a normalised period key suitable for saving.

        Raises ``ValueError`` when no valid 4-digit year is provided.
        """
        normalized = TabuladorConfig.normalize_period_key(period)
        if normalized == '' or normalized == DEFAULT_PERIOD_KEY:
            raise ValueError(
                'Debes indicar un ejercicio valido de 4 digitos para guardar '
                'el tabulador ISR.'
            )
        return normalized

    @staticmethod
    def get_available_periods() -> list:
        """Return a sorted list of available period descriptors."""
        dataset = TabuladorConfig._read_config()
        return TabuladorConfig._build_available_periods(dataset['periods'])

    # --- Private helpers ------------------------------------------------------

    @staticmethod
    def _normalize_number(
        value, as_percent: bool = False
    ) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            number = float(value)
        elif isinstance(value, str):
            clean = value.replace('$', '').replace(',', '').replace(' ', '').replace('%', '')
            if clean == '':
                return None
            try:
                number = float(clean)
            except ValueError:
                return None
        else:
            return None

        if as_percent and number > 1:
            return number / 100.0

        return number

    @staticmethod
    def _read_config() -> dict:
        if not os.path.isfile(CONFIG_FILE):
            return {'periods': {}}

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError:
            return {'periods': {}}

        try:
            decoded = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {'periods': {}}

        if not isinstance(decoded, dict):
            return {'periods': {}}

        # Multi-period format
        if 'periods' in decoded and isinstance(decoded['periods'], dict):
            normalized: dict = {}
            for period_key, info in decoded['periods'].items():
                if (
                    not isinstance(info, dict)
                    or not info.get('rows')
                    or not isinstance(info['rows'], list)
                ):
                    continue
                normalized[period_key] = {
                    'rows': list(info['rows']),
                    'updated_at': info.get('updated_at'),
                }
            return {'periods': normalized}

        # Single-period fallback
        if 'rows' in decoded and isinstance(decoded['rows'], list):
            fallback_period = str(datetime.now().year)
            return {
                'periods': {
                    fallback_period: {
                        'rows': list(decoded['rows']),
                        'updated_at': decoded.get('updated_at'),
                    },
                },
            }

        return {'periods': {}}

    @staticmethod
    def _write_dataset(dataset: dict) -> None:
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
            except OSError:
                raise RuntimeError(
                    'No se pudo preparar la carpeta de configuracion del tabulador ISR.'
                )

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)
        except OSError:
            raise RuntimeError('No se pudo guardar el tabulador ISR.')

    @staticmethod
    def _store_period_rows(period_key: str, rows: list) -> dict:
        dataset = TabuladorConfig._read_config()
        dataset['periods'][period_key] = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'rows': list(rows),
        }
        TabuladorConfig._write_dataset(dataset)
        return dataset

    @staticmethod
    def _build_available_periods(periods: dict) -> list:
        result: List[dict] = []

        for period_key, info in periods.items():
            if re.match(r'^\d{4}$', period_key):
                label = f'Ejercicio {period_key}'
            elif period_key == DEFAULT_PERIOD_KEY:
                label = 'Sin ejercicio'
            else:
                label = f'Ejercicio especial ({period_key})'

            rows_list = info.get('rows')
            result.append({
                'period': period_key,
                'label': label,
                'rows': len(rows_list) if isinstance(rows_list, list) else 0,
                'updated_at': info.get('updated_at'),
            })

        # Sort: numeric year periods first (descending), then others by label
        def sort_key(item):
            is_year = bool(re.match(r'^\d{4}$', item['period']))
            if is_year:
                # Negative year for descending order; group 0 = years first
                return (0, -int(item['period']), item['label'])
            return (1, 0, item['label'])

        result.sort(key=sort_key)
        return result

    @staticmethod
    def _resolve_default_period(periods: dict) -> str:
        numeric = [k for k in periods if re.match(r'^\d{4}$', k)]
        if numeric:
            numeric.sort(reverse=True)
            return numeric[0]

        # Fallback to first available key
        return next(iter(periods))
