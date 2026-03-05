"""Filtered package reader using Python's zipfile module.

Provides the core ZIP reading logic, using a file filter to determine
which entries to return.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from typing import Any, Dict, Generator, Optional

from app.sat.package_reader.internal.file_filters import (
    FileFilterInterface,
    NullFileFilter,
)


class PackageReaderError(Exception):
    """Base exception for package reader errors."""
    pass


class OpenZipFileError(PackageReaderError):
    """Raised when a ZIP file cannot be opened."""

    def __init__(self, filename: str, message: str = '') -> None:
        self.filename = filename
        msg = message or f'Unable to open Zip file {filename}'
        super().__init__(msg)


class CreateTemporaryZipFileError(PackageReaderError):
    """Raised when a temporary ZIP file cannot be created."""
    pass


class FilteredPackageReader:
    """Generic package reader that iterates ZIP entries, applying a
    :class:`FileFilterInterface` to decide which files to include.
    """

    def __init__(self, filename: str, archive: zipfile.ZipFile) -> None:
        """Create a FilteredPackageReader.

        Use :meth:`create_from_file` or :meth:`create_from_contents` instead.

        Args:
            filename: The path to the ZIP file.
            archive: An open ``ZipFile`` object.
        """
        self._filename = filename
        self._archive = archive
        self._filter: FileFilterInterface = NullFileFilter()
        self._remove_on_destruct = False

    def __del__(self) -> None:
        """Remove the temporary file if this reader was created from contents."""
        try:
            self._archive.close()
        except Exception:
            pass
        if self._remove_on_destruct:
            try:
                os.unlink(self._filename)
            except OSError:
                pass

    @classmethod
    def create_from_file(cls, filename: str) -> FilteredPackageReader:
        """Open a ZIP file from disk.

        Args:
            filename: Path to the ZIP file.

        Returns:
            A new FilteredPackageReader.

        Raises:
            OpenZipFileError: If the file cannot be opened as a ZIP.
        """
        try:
            archive = zipfile.ZipFile(filename, 'r')
        except (zipfile.BadZipFile, FileNotFoundError, OSError) as exc:
            raise OpenZipFileError(filename, str(exc)) from exc
        return cls(filename, archive)

    @classmethod
    def create_from_contents(cls, content: bytes) -> FilteredPackageReader:
        """Create a temporary ZIP file from raw bytes and open it.

        The temporary file is automatically deleted when this reader is
        garbage collected.

        Args:
            content: The raw ZIP file bytes.

        Returns:
            A new FilteredPackageReader.

        Raises:
            CreateTemporaryZipFileError: If the temporary file cannot be created.
            OpenZipFileError: If the temporary file cannot be opened as a ZIP.
        """
        try:
            fd, tmpfile = tempfile.mkstemp()
            os.close(fd)
        except OSError as exc:
            raise CreateTemporaryZipFileError(
                f'Cannot create a temporary file: {exc}'
            ) from exc

        try:
            with open(tmpfile, 'wb') as f:
                f.write(content)
        except OSError as exc:
            os.unlink(tmpfile)
            raise CreateTemporaryZipFileError(
                f'Cannot store contents on temporary file: {exc}'
            ) from exc

        try:
            reader = cls.create_from_file(tmpfile)
        except OpenZipFileError:
            os.unlink(tmpfile)
            raise

        reader._remove_on_destruct = True
        return reader

    def file_contents(self) -> Generator[str, None, None]:
        """Iterate file contents inside the ZIP that pass the filter.

        Yields:
            The decoded string content of each qualifying file.
        """
        file_filter = self.get_filter()
        for info in self._archive.infolist():
            filename = info.filename
            if not file_filter.filter_filename(filename):
                continue

            raw = self._archive.read(filename)
            try:
                contents = raw.decode('utf-8')
            except UnicodeDecodeError:
                contents = raw.decode('latin-1')

            if not file_filter.filter_contents(contents):
                continue

            yield contents

    def count(self) -> int:
        """Return the number of files that pass the filter."""
        return sum(1 for _ in self.file_contents())

    def get_filename(self) -> str:
        """Return the path to the underlying ZIP file."""
        return self._filename

    def get_filter(self) -> FileFilterInterface:
        """Return the current file filter."""
        return self._filter

    def set_filter(self, file_filter: FileFilterInterface) -> None:
        """Set the file filter.

        Args:
            file_filter: The new filter to use.
        """
        self._filter = file_filter

    def change_filter(self, file_filter: FileFilterInterface) -> FileFilterInterface:
        """Set a new filter and return the previous one.

        Args:
            file_filter: The new filter to use.

        Returns:
            The previously set filter.
        """
        previous = self._filter
        self._filter = file_filter
        return previous

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        files: Dict[str, str] = {}
        for contents in self.file_contents():
            files[f'file-{len(files)}'] = contents
        return {
            'source': self.get_filename(),
            'files': files,
        }
