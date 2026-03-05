"""Metadata content reader.

Iterates over a preprocessed metadata CSV file and yields
:class:`~app.sat.package_reader.metadata_item.MetadataItem` objects.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

from typing import Generator, Optional, TYPE_CHECKING

from app.sat.package_reader.internal.csv_reader import CsvReader
from app.sat.package_reader.internal.metadata_preprocessor import MetadataPreprocessor
from app.sat.package_reader.internal.third_parties import ThirdPartiesRecords
from app.sat.package_reader.metadata_item import MetadataItem


class MetadataContent:
    """Reads a metadata CSV and produces MetadataItem objects."""

    def __init__(
        self,
        csv_reader: CsvReader,
        third_parties: ThirdPartiesRecords,
    ) -> None:
        """Create a MetadataContent.

        Args:
            csv_reader: The CSV reader positioned on the metadata file.
            third_parties: Third-party records to augment each item with.
        """
        self._csv_reader = csv_reader
        self._third_parties = third_parties

    @classmethod
    def create_from_contents(
        cls,
        contents: str,
        third_parties: Optional[ThirdPartiesRecords] = None,
    ) -> MetadataContent:
        """Create from raw CSV text, applying preprocessing fixes.

        Args:
            contents: The raw metadata CSV text.
            third_parties: Optional third-party records.

        Returns:
            A new MetadataContent instance.
        """
        if third_parties is None:
            third_parties = ThirdPartiesRecords.create_empty()

        preprocessor = MetadataPreprocessor(contents)
        preprocessor.fix()

        csv_reader = CsvReader.create_from_contents(preprocessor.get_contents())
        return cls(csv_reader, third_parties)

    def each_item(self) -> Generator[MetadataItem, None, None]:
        """Iterate over every metadata record as a :class:`MetadataItem`.

        Yields:
            MetadataItem instances with lower-case-first-letter keys.
        """
        for data in self._csv_reader.records():
            data = self._third_parties.add_to_data(data)
            data = self._change_keys_first_letter_lower(data)
            yield MetadataItem(data)

    @staticmethod
    def _change_keys_first_letter_lower(data: dict) -> dict:
        """Return a new dict with every key's first letter lowered.

        For example, ``{'Uuid': '...'}`` becomes ``{'uuid': '...'}``.
        """
        return {
            (k[0].lower() + k[1:] if k else k): v
            for k, v in data.items()
        }
