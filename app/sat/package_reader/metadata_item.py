"""Metadata DTO object.

A simple dictionary wrapper for metadata records, providing
attribute-style access and JSON serialization.
"""

from __future__ import annotations

from typing import Any, Dict


class MetadataItem:
    """A metadata record from the SAT download package.

    Provides dictionary-style and attribute-style access to fields such
    as ``uuid``, ``rfcEmisor``, ``nombreEmisor``, ``rfcReceptor``,
    ``nombreReceptor``, ``rfcPac``, ``fechaEmision``,
    ``fechaCertificacionSat``, ``monto``, ``efectoComprobante``,
    ``estatus``, ``fechaCancelacion``, ``rfcACuentaTerceros``,
    ``nombreACuentaTerceros``.
    """

    def __init__(self, data: Dict[str, str]) -> None:
        """Create a MetadataItem.

        Args:
            data: A dict mapping field names to string values.
        """
        self._data = data

    def __getattr__(self, name: str) -> str:
        """Attribute-style access to fields.

        Returns an empty string for unknown fields.
        """
        if name.startswith('_'):
            raise AttributeError(name)
        return self._data.get(name, '')

    def all(self) -> Dict[str, str]:
        """Return all fields as a dictionary."""
        return dict(self._data)

    def get(self, key: str) -> str:
        """Return a single field value, or empty string if absent.

        Args:
            key: The field name.

        Returns:
            The field value, or ``''`` if the key is not present.
        """
        return self._data.get(key, '')

    @property
    def uuid(self) -> str:
        """Shortcut property for the UUID field."""
        return self._data.get('uuid', '')

    def to_dict(self) -> Dict[str, str]:
        """Return a dictionary representation for JSON serialization.

        The ``uuid`` key is always first.
        """
        result = {'uuid': self.get('uuid')}
        result.update(self._data)
        return result

    def __repr__(self) -> str:
        return f'MetadataItem(uuid={self.uuid!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MetadataItem):
            return NotImplemented
        return self._data == other._data
