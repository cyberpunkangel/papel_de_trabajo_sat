"""File filters for package readers.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


class FileFilterInterface(ABC):
    """Contract for filtering files inside a ZIP package by name or content."""

    @abstractmethod
    def filter_filename(self, filename: str) -> bool:
        """Return True if the filename passes the filter."""
        ...

    @abstractmethod
    def filter_contents(self, contents: str) -> bool:
        """Return True if the file contents pass the filter."""
        ...


class NullFileFilter(FileFilterInterface):
    """Null-object filter that accepts every file."""

    def filter_filename(self, filename: str) -> bool:
        return True

    def filter_contents(self, contents: str) -> bool:
        return True


class CfdiFileFilter(FileFilterInterface):
    """Filter that accepts XML files containing a valid CFDI with a UUID."""

    _FILENAME_PATTERN = re.compile(r'^[^/\\]+\.xml', re.IGNORECASE)

    def filter_filename(self, filename: str) -> bool:
        return bool(self._FILENAME_PATTERN.match(filename))

    def filter_contents(self, contents: str) -> bool:
        # Import here to avoid circular dependency at module level
        from app.sat.package_reader.cfdi_package_reader import CfdiPackageReader
        return CfdiPackageReader.obtain_uuid_from_xml_cfdi(contents) != ''


class MetadataFileFilter(FileFilterInterface):
    """Filter that accepts .txt metadata files with the expected header."""

    _FILENAME_PATTERN = re.compile(r'^[^/\\]+\.txt', re.IGNORECASE)

    def filter_filename(self, filename: str) -> bool:
        return bool(self._FILENAME_PATTERN.match(filename))

    def filter_contents(self, contents: str) -> bool:
        return contents.startswith('Uuid~RfcEmisor~')


class ThirdPartiesFileFilter(FileFilterInterface):
    """Filter that accepts third-party .txt files with the expected header."""

    _FILENAME_PATTERN = re.compile(r'^[^/\\]+_tercero\.txt', re.IGNORECASE)

    def filter_filename(self, filename: str) -> bool:
        return bool(self._FILENAME_PATTERN.match(filename))

    def filter_contents(self, contents: str) -> bool:
        return contents.startswith('Uuid~RfcACuentaTerceros~NombreACuentaTerceros')
