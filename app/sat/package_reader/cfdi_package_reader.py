"""CFDI package reader.

Reads a ZIP package containing CFDI XML files, iterating them as
``(uuid, xml_content)`` pairs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Generator, Tuple

from app.sat.package_reader.internal.file_filters import CfdiFileFilter
from app.sat.package_reader.internal.filtered_package_reader import FilteredPackageReader


class CfdiPackageReader:
    """Reads a CFDI package (ZIP containing XML files).

    Provides iteration over ``(uuid, xml_content)`` pairs and direct
    access to the raw file contents.
    """

    _UUID_PATTERN = re.compile(
        r':Complemento.*?:TimbreFiscalDigital.*?UUID="(?P<uuid>[-a-zA-Z0-9]{36})"',
        re.DOTALL,
    )

    def __init__(self, package_reader: FilteredPackageReader) -> None:
        """Create a CfdiPackageReader.

        Use :meth:`create_from_file` or :meth:`create_from_contents` instead.
        """
        self._package_reader = package_reader

    @classmethod
    def create_from_file(cls, filename: str) -> CfdiPackageReader:
        """Open a CFDI package from a ZIP file on disk.

        Args:
            filename: Path to the ZIP file.

        Returns:
            A new CfdiPackageReader.
        """
        reader = FilteredPackageReader.create_from_file(filename)
        reader.set_filter(CfdiFileFilter())
        return cls(reader)

    @classmethod
    def create_from_contents(cls, content: bytes) -> CfdiPackageReader:
        """Open a CFDI package from raw ZIP bytes.

        Args:
            content: The raw ZIP file bytes.

        Returns:
            A new CfdiPackageReader.
        """
        reader = FilteredPackageReader.create_from_contents(content)
        reader.set_filter(CfdiFileFilter())
        return cls(reader)

    def cfdis(self) -> Generator[Tuple[str, str], None, None]:
        """Iterate the CFDIs in the package.

        Yields:
            Tuples of ``(uuid, xml_content)`` for each CFDI file.
        """
        for content in self._package_reader.file_contents():
            uuid = self.obtain_uuid_from_xml_cfdi(content)
            yield uuid, content

    def get_filename(self) -> str:
        """Return the path to the underlying ZIP file."""
        return self._package_reader.get_filename()

    def count(self) -> int:
        """Return the number of CFDIs in the package."""
        return sum(1 for _ in self.cfdis())

    def file_contents(self) -> Generator[str, None, None]:
        """Iterate the raw file contents (XML strings)."""
        yield from self._package_reader.file_contents()

    @staticmethod
    def obtain_uuid_from_xml_cfdi(xml_content: str) -> str:
        """Extract the UUID from a CFDI XML's ``TimbreFiscalDigital`` complement.

        Args:
            xml_content: The raw XML string.

        Returns:
            The lowercase UUID, or an empty string if not found.
        """
        pattern = re.compile(
            r':Complemento.*?:TimbreFiscalDigital.*?UUID="(?P<uuid>[-a-zA-Z0-9]{36})"',
            re.DOTALL,
        )
        match = pattern.search(xml_content)
        if match:
            return match.group('uuid').lower()
        return ''

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        base = self._package_reader.to_dict()
        base['cfdis'] = dict(self.cfdis())
        return base
