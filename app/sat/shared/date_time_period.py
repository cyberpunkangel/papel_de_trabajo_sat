"""Defines a period of time by start and end DateTime values."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional, Union

from .date_time import DateTime


class DateTimePeriod:
    """Defines a period of time by start of period and end of period values."""

    def __init__(self, start: DateTime, end: DateTime) -> None:
        """Create a DateTimePeriod instance.

        Args:
            start: The start of the period.
            end: The end of the period.

        Raises:
            ValueError: If the end date is before the start date.
        """
        if end.compare_to(start) < 0:
            raise ValueError('The final date must be greater than the initial date')
        self._start: DateTime = start
        self._end: DateTime = end

    @classmethod
    def create(cls, start: DateTime, end: DateTime) -> DateTimePeriod:
        """Create a new instance of the period object.

        Args:
            start: The start DateTime.
            end: The end DateTime.
        """
        return cls(start, end)

    @classmethod
    def create_from_values(
        cls,
        start: Union[None, int, str, dt.datetime] = None,
        end: Union[None, int, str, dt.datetime] = None,
    ) -> DateTimePeriod:
        """Create a new instance of the period object from raw values.

        Arguments can be integers (timestamps), strings, datetime objects, or None.

        Args:
            start: The start value.
            end: The end value.
        """
        return cls.create(DateTime.create(start), DateTime.create(end))

    @property
    def start(self) -> DateTime:
        """Return the start of the period."""
        return self._start

    @property
    def end(self) -> DateTime:
        """Return the end of the period."""
        return self._end

    def get_start(self) -> DateTime:
        """Return the start of the period."""
        return self._start

    def get_end(self) -> DateTime:
        """Return the end of the period."""
        return self._end

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'start': self._start.to_dict(),
            'end': self._end.to_dict(),
        }

    def __repr__(self) -> str:
        return (
            f'DateTimePeriod(start={self._start.format_sat()!r}, '
            f'end={self._end.format_sat()!r})'
        )
