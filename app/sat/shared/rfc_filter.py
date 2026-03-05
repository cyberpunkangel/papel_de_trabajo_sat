"""RFC filter value objects for SAT web service queries."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional


# RFC validation regex used across the project
_RFC_PATTERN = re.compile(r'^[A-Z\u00d1&]{3,4}\d{6}[A-Z0-9]{3}$')


class AbstractRfcFilter:
    """Base class for RFC filter value objects.

    Validates the RFC format using the pattern ``^[A-ZN&]{3,4}\\d{6}[A-Z0-9]{3}$``
    (where N includes the Spanish letter).
    """

    def __init__(self, value: Optional[str]) -> None:
        """Create an RFC filter. Use ``create()`` or ``empty()`` factory methods.

        Args:
            value: The validated RFC string, or None for an empty filter.
        """
        self._value: Optional[str] = value

    @classmethod
    def create(cls, value: str) -> AbstractRfcFilter:
        """Create an RFC filter from a string value.

        Args:
            value: The RFC string to validate and store.

        Raises:
            ValueError: If the RFC string does not match the expected format.

        Returns:
            A new instance of the subclass.
        """
        if not _RFC_PATTERN.match(value):
            raise ValueError('RFC is invalid')
        return cls(value)

    @classmethod
    def empty(cls) -> AbstractRfcFilter:
        """Create an empty RFC filter with no value."""
        return cls(None)

    @staticmethod
    def check(value: str) -> bool:
        """Check whether a string is a valid RFC.

        Args:
            value: The string to validate.

        Returns:
            True if the string matches the RFC format, False otherwise.
        """
        return bool(_RFC_PATTERN.match(value))

    def is_empty(self) -> bool:
        """Return True if this filter has no RFC value."""
        return self._value is None

    def get_value(self) -> str:
        """Return the RFC string, or empty string if empty."""
        if self._value is None:
            return ''
        return self._value

    @property
    def value(self) -> str:
        """Return the RFC string, or empty string if empty."""
        return self.get_value()

    def to_dict(self) -> Optional[str]:
        """Return the RFC value for JSON serialization."""
        return self._value

    def __repr__(self) -> str:
        class_name = type(self).__name__
        return f'{class_name}({self._value!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractRfcFilter):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class RfcMatch(AbstractRfcFilter):
    """RFC filter for matching queries. Extends AbstractRfcFilter without changes."""

    @classmethod
    def create(cls, value: str) -> RfcMatch:
        """Create an RfcMatch from a string value.

        Args:
            value: The RFC string to validate and store.

        Raises:
            ValueError: If the RFC string does not match the expected format.
        """
        if not _RFC_PATTERN.match(value):
            raise ValueError('RFC is invalid')
        return cls(value)

    @classmethod
    def empty(cls) -> RfcMatch:
        """Create an empty RfcMatch with no value."""
        return cls(None)


class RfcOnBehalf(AbstractRfcFilter):
    """RFC filter for on-behalf-of queries. Extends AbstractRfcFilter without changes."""

    @classmethod
    def create(cls, value: str) -> RfcOnBehalf:
        """Create an RfcOnBehalf from a string value.

        Args:
            value: The RFC string to validate and store.

        Raises:
            ValueError: If the RFC string does not match the expected format.
        """
        if not _RFC_PATTERN.match(value):
            raise ValueError('RFC is invalid')
        return cls(value)

    @classmethod
    def empty(cls) -> RfcOnBehalf:
        """Create an empty RfcOnBehalf with no value."""
        return cls(None)


class RfcMatches:
    """A collection of RfcMatch objects.

    Stores unique, non-empty RfcMatch values. Supports iteration, counting,
    and JSON serialization.
    """

    def __init__(self, items: List[RfcMatch]) -> None:
        """Create from a list of RfcMatch items (internal use).

        Use ``create()`` or ``create_from_values()`` factory methods instead.

        Args:
            items: The list of validated, unique, non-empty RfcMatch items.
        """
        self._items: List[RfcMatch] = list(items)
        self._count: int = len(self._items)

    @classmethod
    def create(cls, *items: RfcMatch) -> RfcMatches:
        """Create from RfcMatch instances, filtering out empties and duplicates.

        Args:
            items: Variable number of RfcMatch instances.

        Returns:
            A new RfcMatches collection with unique, non-empty entries.
        """
        seen: Dict[str, RfcMatch] = {}
        for item in items:
            key = item.get_value()
            if not item.is_empty() and key not in seen:
                seen[key] = item
        return cls(list(seen.values()))

    @classmethod
    def create_from_values(cls, *values: str) -> RfcMatches:
        """Create from string RFC values, filtering out empties and duplicates.

        Empty strings create empty RfcMatch objects (which are then filtered out).

        Args:
            values: Variable number of RFC strings.

        Returns:
            A new RfcMatches collection with unique, non-empty entries.
        """
        items = [
            RfcMatch.empty() if value == '' else RfcMatch.create(value)
            for value in values
        ]
        return cls.create(*items)

    def is_empty(self) -> bool:
        """Return True if the collection has no items."""
        return self._count == 0

    def get_first(self) -> RfcMatch:
        """Return the first item, or an empty RfcMatch if the collection is empty."""
        if self._items:
            return self._items[0]
        return RfcMatch.empty()

    def count(self) -> int:
        """Return the number of items in the collection."""
        return self._count

    def __len__(self) -> int:
        return self._count

    def __iter__(self) -> Iterator[RfcMatch]:
        return iter(self._items)

    def to_dict(self) -> List[Optional[str]]:
        """Return a list representation for JSON serialization."""
        return [item.to_dict() for item in self._items]

    def __repr__(self) -> str:
        return f'RfcMatches(count={self._count})'
