"""Third-party records extractor and container.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

from typing import Dict, Generator, Optional, Tuple, TYPE_CHECKING

from app.sat.package_reader.internal.csv_reader import CsvReader
from app.sat.package_reader.internal.file_filters import ThirdPartiesFileFilter

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# ThirdPartiesExtractor
# ---------------------------------------------------------------------------

class ThirdPartiesExtractor:
    """Extracts third-party data from the ``*_tercero.txt`` file inside a
    SAT download package.
    """

    def __init__(self, csv_reader: CsvReader) -> None:
        self._csv_reader = csv_reader

    @classmethod
    def create_from_package_reader(cls, package_reader: object) -> ThirdPartiesExtractor:
        """Create from a :class:`FilteredPackageReader`.

        Temporarily swaps the reader's filter to :class:`ThirdPartiesFileFilter`
        to locate and read the third-parties file, then restores the
        original filter.

        Args:
            package_reader: Must be a ``FilteredPackageReader`` instance.

        Returns:
            A new ThirdPartiesExtractor with the parsed CSV data.

        Raises:
            TypeError: If *package_reader* is not a FilteredPackageReader.
        """
        # Avoid circular import
        from app.sat.package_reader.internal.filtered_package_reader import FilteredPackageReader

        if not isinstance(package_reader, FilteredPackageReader):
            raise TypeError('PackageReader parameter must be a FilteredPackageReader')

        previous_filter = package_reader.change_filter(ThirdPartiesFileFilter())
        contents = ''
        for file_contents in package_reader.file_contents():
            contents = file_contents
            break
        package_reader.set_filter(previous_filter)

        return cls(CsvReader.create_from_contents(contents))

    def each_record(self) -> Generator[Tuple[str, Dict[str, str]], None, None]:
        """Iterate third-party records.

        Yields:
            Tuples of ``(uuid, {'RfcACuentaTerceros': ..., 'NombreACuentaTerceros': ...})``.
        """
        for data in self._csv_reader.records():
            uuid = str(data.get('Uuid', '')).upper()
            if not uuid:
                continue
            yield uuid, {
                'RfcACuentaTerceros': str(data.get('RfcACuentaTerceros', '')),
                'NombreACuentaTerceros': str(data.get('NombreACuentaTerceros', '')),
            }


# ---------------------------------------------------------------------------
# ThirdPartiesRecords
# ---------------------------------------------------------------------------

class ThirdPartiesRecords:
    """Stores third-party data keyed by UUID (lowercase).

    Provides a method to augment a metadata row with its third-party
    data from this collection.
    """

    def __init__(self, records: Dict[str, Dict[str, str]]) -> None:
        """Create a ThirdPartiesRecords container.

        Args:
            records: A dict mapping lowercase UUIDs to dicts with keys
                ``RfcACuentaTerceros`` and ``NombreACuentaTerceros``.
        """
        self._records = records

    @classmethod
    def create_empty(cls) -> ThirdPartiesRecords:
        """Create an empty records container."""
        return cls({})

    @classmethod
    def create_from_package_reader(cls, package_reader: object) -> ThirdPartiesRecords:
        """Build records from a package reader.

        Args:
            package_reader: A ``FilteredPackageReader`` (or compatible).

        Returns:
            A new ThirdPartiesRecords populated from the ``*_tercero.txt`` file.
        """
        extractor = ThirdPartiesExtractor.create_from_package_reader(package_reader)
        records: Dict[str, Dict[str, str]] = {}
        for uuid, values in extractor.each_record():
            records[cls._format_uuid(uuid)] = values
        return cls(records)

    @staticmethod
    def _format_uuid(uuid: str) -> str:
        return uuid.lower()

    def add_to_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Merge third-party information into a metadata row.

        Looks up the UUID from the ``Uuid`` key in *data* and adds
        ``RfcACuentaTerceros`` and ``NombreACuentaTerceros`` keys.

        Args:
            data: The original metadata row.

        Returns:
            A new dict with the third-party keys merged in.
        """
        uuid = data.get('Uuid', '')
        values = self.get_data_from_uuid(uuid)
        merged = dict(data)
        merged.update(values)
        return merged

    def get_data_from_uuid(self, uuid: str) -> Dict[str, str]:
        """Return the third-party data for a UUID, or empty defaults.

        Args:
            uuid: The UUID to look up (case-insensitive).

        Returns:
            A dict with ``RfcACuentaTerceros`` and ``NombreACuentaTerceros``.
        """
        return self._records.get(self._format_uuid(uuid), {
            'RfcACuentaTerceros': '',
            'NombreACuentaTerceros': '',
        })
