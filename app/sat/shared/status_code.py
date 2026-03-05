"""Defines CodEstatus and Mensaje from SAT web service responses."""

from __future__ import annotations

from typing import Any, Dict


class StatusCode:
    """Defines "CodEstatus" and "Mensaje".

    A simple value object containing the status code and message returned
    by SAT web service operations.
    """

    def __init__(self, code: int, message: str) -> None:
        """Create a StatusCode instance.

        Args:
            code: The SAT "CodEstatus" integer value.
            message: The SAT "Mensaje" text.
        """
        self._code: int = code
        self._message: str = message

    @property
    def code(self) -> int:
        """Contains the value of "CodEstatus"."""
        return self._code

    @property
    def message(self) -> str:
        """Contains the value of "Mensaje"."""
        return self._message

    def get_code(self) -> int:
        """Contains the value of "CodEstatus"."""
        return self._code

    def get_message(self) -> str:
        """Contains the value of "Mensaje"."""
        return self._message

    def is_accepted(self) -> bool:
        """Return True when "CodEstatus" is success.

        The only success code is 5000: Solicitud recibida con exito.
        """
        return 5000 == self._code

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'code': self._code,
            'message': self._message,
        }

    def __repr__(self) -> str:
        return f'StatusCode(code={self._code}, message={self._message!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StatusCode):
            return NotImplemented
        return self._code == other._code and self._message == other._message

    def __hash__(self) -> int:
        return hash((self._code, self._message))
