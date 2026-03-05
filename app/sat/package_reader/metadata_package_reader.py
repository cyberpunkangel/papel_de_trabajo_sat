"""Metadata package reader.

Reads a ZIP package containing metadata CSV files and iterates them as
:class:`~app.sat.package_reader.metadata_item.MetadataItem` objects.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, Tuple

from app.sat.package_reader.internal.file_filters import MetadataFileFilter
from app.sat.package_reader.internal.filtered_package_reader import FilteredPackageReader
from app.sat.package_reader.internal.metadata_content import MetadataContent
from app.sat.package_reader.internal.third_parties import ThirdPartiesRecords
from app.sat.package_reader.metadata_item import MetadataItem


class MetadataPackageReader:
    """Reads a Metadata package (ZIP containing CSV/TXT files).

    Provides iteration over ``(uuid, MetadataItem)`` pairs using the
    SAT's CSV format.
    """

    def __init__(self, package_reader: FilteredPackageReader) -> None:
        """Create a MetadataPackageReader.

        Use :meth:`create_from_file` or :meth:`create_from_contents` instead.
        """
        self._package_reader = package_reader
        self._third_parties = ThirdPartiesRecords.create_from_package_reader(
            self._package_reader
        )

    @classmethod
    def create_from_file(cls, filename: str) -> MetadataPackageReader:
        """Open a Metadata package from a ZIP file on disk.

        Args:
            filename: Path to the ZIP file.

        Returns:
            A new MetadataPackageReader.
        """
        reader = FilteredPackageReader.create_from_file(filename)
        reader.set_filter(MetadataFileFilter())
        return cls(reader)

    @classmethod
    def create_from_contents(cls, content: bytes) -> MetadataPackageReader:
        """Open a Metadata package from raw ZIP bytes.

        Args:
            content: The raw ZIP file bytes.

        Returns:
            A new MetadataPackageReader.
        """
        reader = FilteredPackageReader.create_from_contents(content)
        reader.set_filter(MetadataFileFilter())
        return cls(reader)

    def get_third_parties(self) -> ThirdPartiesRecords:
        """Return the third-party records extracted from the package."""
        return self._third_parties

    def metadata(self) -> Generator[Tuple[str, MetadataItem], None, None]:
        """Iterate metadata items in the package.

        Yields:
            Tuples of ``(uuid, MetadataItem)`` for each record.
        """
        for content in self._package_reader.file_contents():
            reader = MetadataContent.create_from_contents(
                content, self.get_third_parties()
            )
            for item in reader.each_item():
                yield item.uuid, item

    def get_filename(self) -> str:
        """Return the path to the underlying ZIP file."""
        return self._package_reader.get_filename()

    def count(self) -> int:
        """Return the number of metadata items in the package."""
        return sum(1 for _ in self.metadata())

    def file_contents(self) -> Generator[str, None, None]:
        """Iterate the raw file contents (CSV/TXT strings)."""
        yield from self._package_reader.file_contents()

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        base = self._package_reader.to_dict()
        base['metadata'] = {uuid: item.to_dict() for uuid, item in self.metadata()}
        return base
