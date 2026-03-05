"""CSV reader for SAT metadata files.

The SAT metadata CSV format uses ``~`` as the field separator and ``|`` as
the text delimiter (quote character).

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

import csv
import io
from typing import Dict, Generator, List, Optional


class CsvReader:
    """Helper to iterate inside a SAT CSV file.

    The file must have headers on the first line.
    Uses ``~`` as separator and ``|`` as text delimiter.
    """

    def __init__(self, rows: List[List[str]]) -> None:
        """Create a CsvReader from pre-parsed rows.

        Use :meth:`create_from_contents` instead.
        """
        self._rows = rows

    @staticmethod
    def _parse_contents(contents: str) -> List[List[str]]:
        """Parse CSV contents using ``~`` separator and ``|`` quoting."""
        if not contents:
            return []
        reader = csv.reader(
            io.StringIO(contents),
            delimiter='~',
            quotechar='|',
            escapechar='\\',
        )
        rows: List[List[str]] = []
        for row in reader:
            rows.append(row)
        return rows

    @classmethod
    def create_from_contents(cls, contents: str) -> CsvReader:
        """Create a CsvReader from a raw CSV string.

        Args:
            contents: The CSV file contents.

        Returns:
            A new CsvReader instance.
        """
        rows = cls._parse_contents(contents)
        return cls(rows)

    def records(self) -> Generator[Dict[str, str], None, None]:
        """Iterate records as dicts, using the first row as header keys.

        Yields:
            A dictionary mapping header names to row values for each
            data row.
        """
        headers: List[str] = []
        for row in self._rows:
            data = self._normalize_data(row)
            if not data:
                continue

            if not headers:
                headers = data
                continue

            yield self.combine(headers, data)

    @staticmethod
    def _normalize_data(data: List[str]) -> List[str]:
        """Filter to only string values, returning an empty list for invalid data."""
        return [v for v in data if isinstance(v, str)]

    @staticmethod
    def combine(keys: List[str], values: List[str]) -> Dict[str, str]:
        """Like ``dict(zip(keys, values))`` but pads missing keys or values.

        If there are more keys than values, extra values default to ``''``.
        If there are more values than keys, extra keys are named
        ``#extra-01``, ``#extra-02``, etc.

        Args:
            keys: The header names.
            values: The data values.

        Returns:
            An ordered dict mapping keys to values.
        """
        count_keys = len(keys)
        count_values = len(values)

        if count_keys > count_values:
            values = values + [''] * (count_keys - count_values)

        if count_values > count_keys:
            extra_count = count_values - count_keys
            keys = keys + [f'#extra-{i:02d}' for i in range(1, extra_count + 1)]

        return dict(zip(keys, values))
