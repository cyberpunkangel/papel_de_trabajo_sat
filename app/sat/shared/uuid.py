"""Defines a UUID value object."""

from __future__ import annotations

import re
from typing import Dict


class Uuid:
    """Represents a UUID value.

    The UUID is stored in lowercase and validated against the standard
    format ``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx``.
    """

    def __init__(self, value: str) -> None:
        """Private-style constructor. Use ``create()`` or ``empty()`` instead."""
        self._value: str = value

    @classmethod
    def create(cls, value: str) -> Uuid:
        """Create a Uuid from a string value.

        The value is lowercased and validated against the UUID format.

        Args:
            value: The UUID string.

        Raises:
            ValueError: If the value does not match the UUID format.
        """
        value = value.lower()
        pattern = r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$'
        if not re.match(pattern, value):
            raise ValueError('UUID does not have the correct format')
        return cls(value)

    @classmethod
    def empty(cls) -> Uuid:
        """Create an empty Uuid."""
        return cls('')

    @staticmethod
    def check(value: str) -> bool:
        """Check whether a string is a valid UUID.

        Args:
            value: The string to validate.

        Returns:
            True if the string is a valid UUID, False otherwise.
        """
        try:
            Uuid.create(value)
            return True
        except (ValueError, Exception):
            return False

    def is_empty(self) -> bool:
        """Return True if this is an empty UUID."""
        return self._value == ''

    def get_value(self) -> str:
        """Return the UUID string value."""
        return self._value

    @property
    def value(self) -> str:
        """Return the UUID string value."""
        return self._value

    def to_dict(self) -> str:
        """Return the string value for JSON serialization."""
        return self._value

    def __repr__(self) -> str:
        return f'Uuid({self._value!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Uuid):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
