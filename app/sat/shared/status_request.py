"""Defines EstadoSolicitud from SAT web service responses."""

from __future__ import annotations

from typing import Any, Dict, Optional


class StatusRequest:
    """Defines "EstadoSolicitud".

    This is a catalog-style class mapping integer values to known request
    statuses with Spanish messages.
    """

    _VALUES: Dict[int, Dict[str, str]] = {
        1: {'name': 'Accepted', 'message': 'Aceptada'},
        2: {'name': 'InProgress', 'message': 'En proceso'},
        3: {'name': 'Finished', 'message': 'Terminada'},
        4: {'name': 'Failure', 'message': 'Error'},
        5: {'name': 'Rejected', 'message': 'Rechazada'},
        6: {'name': 'Expired', 'message': 'Vencida'},
    }

    _UNDEFINED_ENTRY: Dict[str, str] = {'name': 'Unknown', 'message': 'Desconocida'}

    def __init__(self, value: int) -> None:
        """Create a StatusRequest from its integer value.

        Args:
            value: The "EstadoSolicitud" integer (1-6 for known values).
        """
        self._index: int = value
        entry = self._VALUES.get(value, self._UNDEFINED_ENTRY)
        self._name: str = entry['name']
        self._message: str = entry['message']

    @classmethod
    def get_entries_array(cls) -> Dict[int, Dict[str, str]]:
        """Return the full catalog of known entries."""
        return dict(cls._VALUES)

    def get_value(self) -> int:
        """Contains the "EstadoSolicitud" value."""
        return self._index

    @property
    def value(self) -> int:
        """Contains the "EstadoSolicitud" value."""
        return self._index

    def get_name(self) -> str:
        """Contains the internal name (e.g. 'Accepted', 'InProgress')."""
        return self._name

    def get_message(self) -> str:
        """Contains the known message in Spanish."""
        return self._message

    def get_entry_id(self) -> str:
        """Return the entry identifier (the name)."""
        return self._name

    def is_accepted(self) -> bool:
        """Check if the status is Accepted (1)."""
        return self._index == 1

    def is_in_progress(self) -> bool:
        """Check if the status is InProgress (2)."""
        return self._index == 2

    def is_finished(self) -> bool:
        """Check if the status is Finished (3)."""
        return self._index == 3

    def is_failure(self) -> bool:
        """Check if the status is Failure (4)."""
        return self._index == 4

    def is_rejected(self) -> bool:
        """Check if the status is Rejected (5)."""
        return self._index == 5

    def is_expired(self) -> bool:
        """Check if the status is Expired (6)."""
        return self._index == 6

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'value': self._index,
            'message': self._message,
        }

    def __repr__(self) -> str:
        return f'StatusRequest(value={self._index}, name={self._name!r}, message={self._message!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StatusRequest):
            return NotImplemented
        return self._index == other._index

    def __hash__(self) -> int:
        return hash(self._index)
