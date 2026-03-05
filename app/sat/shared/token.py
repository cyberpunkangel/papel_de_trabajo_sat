"""Defines a Token as given from SAT."""

from __future__ import annotations

from typing import Any, Dict

from app.sat.shared.date_time import DateTime


class Token:
    """Defines a Token as given from SAT.

    A token has a creation date, an expiration date, and a string value.
    It is valid when it contains a non-empty value and is not expired.
    """

    def __init__(self, created: DateTime, expires: DateTime, value: str) -> None:
        """Create a Token instance.

        Args:
            created: The token creation date.
            expires: The token expiration date.
            value: The token string value.

        Raises:
            ValueError: If the expiration date is before the creation date.
        """
        if expires.compare_to(created) < 0:
            raise ValueError('Cannot create a token with expiration lower than creation')
        self._created: DateTime = created
        self._expires: DateTime = expires
        self._value: str = value

    @classmethod
    def empty(cls) -> Token:
        """Create an empty token with zero timestamps and no value."""
        return cls(DateTime.create(0), DateTime.create(0), '')

    @property
    def created(self) -> DateTime:
        """Token creation date."""
        return self._created

    @property
    def expires(self) -> DateTime:
        """Token expiration date."""
        return self._expires

    @property
    def value(self) -> str:
        """Token value."""
        return self._value

    def get_created(self) -> DateTime:
        """Token creation date."""
        return self._created

    def get_expires(self) -> DateTime:
        """Token expiration date."""
        return self._expires

    def get_value(self) -> str:
        """Token value."""
        return self._value

    def is_value_empty(self) -> bool:
        """A token is empty if it does not contain an internal value."""
        return '' == self._value

    def is_expired(self) -> bool:
        """A token is expired if the expiration date is less than the current time."""
        return self._expires.compare_to(DateTime.now()) < 0

    def is_valid(self) -> bool:
        """A token is valid if it contains a value and is not expired."""
        return not self.is_value_empty() and not self.is_expired()

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'created': self._created.to_dict(),
            'expires': self._expires.to_dict(),
            'value': self._value,
        }

    def __repr__(self) -> str:
        return (
            f'Token(created={self._created.format_sat()!r}, '
            f'expires={self._expires.format_sat()!r}, '
            f'value={self._value!r})'
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return NotImplemented
        return (
            self._created == other._created
            and self._expires == other._expires
            and self._value == other._value
        )
