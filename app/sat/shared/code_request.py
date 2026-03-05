"""Defines CodigoEstadoSolicitud from SAT web service responses."""

from __future__ import annotations

from typing import Any, Dict


class CodeRequest:
    """Defines "CodigoEstadoSolicitud".

    This is a catalog-style class mapping integer codes to known request
    code statuses with Spanish messages.
    """

    _VALUES: Dict[int, Dict[str, str]] = {
        5000: {
            'name': 'Accepted',
            'message': 'Solicitud recibida con \u00e9xito',
        },
        5002: {
            'name': 'Exhausted',
            'message': 'Se agot\u00f3 las solicitudes de por vida:'
                       ' M\u00e1ximo para solicitudes con los mismos par\u00e1metros',
        },
        5003: {
            'name': 'MaximumLimitReaded',
            'message': 'Tope m\u00e1ximo:'
                       ' Indica que se est\u00e1 superando el tope m\u00e1ximo de CFDI o Metadata',
        },
        5004: {
            'name': 'EmptyResult',
            'message': 'No se encontr\u00f3 la informaci\u00f3n:'
                       ' Indica que no gener\u00f3 paquetes por falta de informaci\u00f3n.',
        },
        5005: {
            'name': 'Duplicated',
            'message': 'Solicitud duplicada:'
                       ' Si existe una solicitud vigente con los mismos par\u00e1metros',
        },
    }

    _UNDEFINED_ENTRY: Dict[str, str] = {'name': 'Unknown', 'message': 'Desconocida'}

    def __init__(self, value: int) -> None:
        """Create a CodeRequest from its integer value.

        Args:
            value: The "CodigoEstadoSolicitud" integer (5000, 5002-5005 for known values).
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
        """Contains the value of "CodigoEstadoSolicitud"."""
        return self._index

    @property
    def value(self) -> int:
        """Contains the value of "CodigoEstadoSolicitud"."""
        return self._index

    def get_name(self) -> str:
        """Contains the internal name (e.g. 'Accepted', 'Exhausted')."""
        return self._name

    def get_message(self) -> str:
        """Contains the known message in Spanish."""
        return self._message

    def get_entry_id(self) -> str:
        """Return the entry identifier (the name)."""
        return self._name

    def is_accepted(self) -> bool:
        """Check if the code is Accepted (5000)."""
        return self._index == 5000

    def is_exhausted(self) -> bool:
        """Check if the code is Exhausted (5002)."""
        return self._index == 5002

    def is_maximum_limit_readed(self) -> bool:
        """Check if the code is MaximumLimitReaded (5003)."""
        return self._index == 5003

    def is_empty_result(self) -> bool:
        """Check if the code is EmptyResult (5004)."""
        return self._index == 5004

    def is_duplicated(self) -> bool:
        """Check if the code is Duplicated (5005)."""
        return self._index == 5005

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'value': self._index,
            'message': self._message,
        }

    def __repr__(self) -> str:
        return f'CodeRequest(value={self._index}, name={self._name!r}, message={self._message!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeRequest):
            return NotImplemented
        return self._index == other._index

    def __hash__(self) -> int:
        return hash(self._index)
