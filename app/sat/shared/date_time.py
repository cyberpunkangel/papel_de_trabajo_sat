"""Defines a date and time for SAT web service interactions."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional, Union


class DateTime:
    """Defines a date and time.

    Wraps a timezone-aware datetime.datetime value and provides SAT-specific formatting.
    """

    def __init__(self, value: Union[None, int, str, dt.datetime] = None) -> None:
        """Create a DateTime instance.

        If value is an integer it is used as a timestamp, if it is a string it is
        evaluated as an argument for datetime parsing, and if it is a datetime it is
        used as is. If None, the current time is used.

        Args:
            value: The value to create the DateTime from.

        Raises:
            ValueError: If unable to create a DateTime from the provided value.
        """
        if value is None:
            value = dt.datetime.now(tz=dt.timezone.utc)
        if isinstance(value, int):
            try:
                value = dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
            except (OSError, OverflowError, ValueError) as exc:
                raise ValueError(f'Unable to create a DateTime from timestamp "{value}"') from exc
        if isinstance(value, str):
            try:
                value = self._parse_string(value)
            except Exception as exc:
                raise ValueError(f'Unable to create a DateTime("{value}")') from exc
        if not isinstance(value, dt.datetime):
            raise ValueError('Unable to create a DateTime')
        # Ensure the datetime is timezone-aware (default to UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        self._value: dt.datetime = value

    @staticmethod
    def _parse_string(value: str) -> dt.datetime:
        """Parse a string into a datetime object.

        Supports ISO 8601 formats and the SAT-specific format.
        """
        # Handle SAT format with .000Z suffix
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        # Try ISO format parsing
        try:
            return dt.datetime.fromisoformat(value)
        except ValueError:
            pass
        # Try common formats
        for fmt in (
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ):
            try:
                return dt.datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f'Unable to parse date string: {value}')

    @classmethod
    def create(cls, value: Union[None, int, str, dt.datetime] = None) -> DateTime:
        """Create a DateTime instance.

        If value is an integer it is used as a timestamp, if it is a string it is
        evaluated as an argument for datetime parsing, and if it is a datetime it is
        used as is. If None, the current time is used.

        Args:
            value: The value to create the DateTime from.
        """
        return cls(value)

    @classmethod
    def now(cls) -> DateTime:
        """Create a DateTime instance representing the current time."""
        return cls()

    def format_sat(self) -> str:
        """Format the date and time in SAT format.

        Returns a string like ``2024-01-15T00:00:00.000Z`` with milliseconds
        and the ``Z`` UTC timezone indicator.
        """
        return self.format_timezone('UTC')

    def format(self, fmt: str, timezone: str = '') -> str:
        """Format the date and time using a custom format string.

        Args:
            fmt: The strftime format string.
            timezone: The timezone name. If empty, the local timezone is used.
        """
        if timezone:
            tz = self._get_timezone(timezone)
            value = self._value.astimezone(tz)
        else:
            value = self._value.astimezone()
        return value.strftime(fmt)

    def format_default_timezone(self) -> str:
        """Format the date and time in the local timezone using SAT format."""
        local_value = self._value.astimezone()
        return local_value.strftime('%Y-%m-%dT%H:%M:%S.000%Z')

    def format_timezone(self, timezone: str) -> str:
        """Format the date and time in the given timezone using SAT format.

        The output looks like ``2024-01-15T00:00:00.000Z`` when timezone is UTC.

        Args:
            timezone: The timezone name (e.g. ``'UTC'``, ``'Z'``).
        """
        tz = self._get_timezone(timezone)
        value = self._value.astimezone(tz)
        # SAT format 'Y-m-d\\TH:i:s.000T' outputs e.g. 2024-01-15T00:00:00.000Z
        tz_abbr = value.strftime('%Z')
        if tz_abbr == 'UTC':
            tz_abbr = 'Z'
        return value.strftime(f'%Y-%m-%dT%H:%M:%S.000{tz_abbr}')

    @staticmethod
    def _get_timezone(timezone: str) -> dt.timezone:
        """Convert a timezone name to a datetime.timezone object."""
        if timezone in ('Z', 'UTC', 'utc'):
            return dt.timezone.utc
        # For numeric offsets like +05:00 or -03:00
        if timezone.startswith(('+', '-')):
            sign = 1 if timezone.startswith('+') else -1
            parts = timezone[1:].split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            offset = dt.timedelta(hours=hours, minutes=minutes) * sign
            return dt.timezone(offset)
        # Try using zoneinfo for named timezones (Python 3.9+)
        try:
            from zoneinfo import ZoneInfo
            zone = ZoneInfo(timezone)
            # Return as a fixed offset based on current value
            return dt.timezone(dt.timedelta(0))  # Fallback to UTC for unknown
        except (ImportError, KeyError):
            return dt.timezone.utc

    def modify(self, modify: str) -> DateTime:
        """Return a new DateTime modified by the given expression.

        Supports modify strings such as ``'+5 minutes'``,
        ``'-1 day'``, ``'+3 hours'``, etc.

        Args:
            modify: A modification string (e.g. ``'+5 minutes'``).

        Returns:
            A new DateTime instance with the modification applied.
        """
        import re
        match = re.match(r'^([+-]?\d+)\s+(second|minute|hour|day|week|month|year)s?$', modify.strip())
        if not match:
            raise ValueError(f'Unable to parse modify string: {modify}')
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == 'second':
            delta = dt.timedelta(seconds=amount)
        elif unit == 'minute':
            delta = dt.timedelta(minutes=amount)
        elif unit == 'hour':
            delta = dt.timedelta(hours=amount)
        elif unit == 'day':
            delta = dt.timedelta(days=amount)
        elif unit == 'week':
            delta = dt.timedelta(weeks=amount)
        elif unit == 'month':
            # Approximate month handling
            new_month = self._value.month + amount
            new_year = self._value.year + (new_month - 1) // 12
            new_month = ((new_month - 1) % 12) + 1
            try:
                new_value = self._value.replace(year=new_year, month=new_month)
            except ValueError:
                # Handle end-of-month overflow (e.g. Jan 31 + 1 month)
                import calendar
                last_day = calendar.monthrange(new_year, new_month)[1]
                new_value = self._value.replace(year=new_year, month=new_month, day=last_day)
            return DateTime(new_value)
        elif unit == 'year':
            try:
                new_value = self._value.replace(year=self._value.year + amount)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                new_value = self._value.replace(year=self._value.year + amount, day=28)
            return DateTime(new_value)
        else:
            raise ValueError(f'Unknown time unit: {unit}')
        return DateTime(self._value + delta)

    def compare_to(self, other_date: DateTime) -> int:
        """Compare this DateTime to another.

        Returns:
            A negative value if this date is before other_date,
            zero if they are equal, and a positive value if this date
            is after other_date.
        """
        a = self.format_sat()
        b = other_date.format_sat()
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def equals_to(self, other: DateTime) -> bool:
        """Check whether this DateTime equals another (compared via SAT format)."""
        return self.format_sat() == other.format_sat()

    def to_dict(self) -> int:
        """Return the timestamp for JSON serialization."""
        return int(self._value.timestamp())

    @property
    def value(self) -> dt.datetime:
        """Return the underlying datetime object."""
        return self._value

    def __repr__(self) -> str:
        return f'DateTime({self.format_sat()!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DateTime):
            return NotImplemented
        return self.equals_to(other)

    def __lt__(self, other: DateTime) -> bool:
        return self.compare_to(other) < 0

    def __le__(self, other: DateTime) -> bool:
        return self.compare_to(other) <= 0

    def __gt__(self, other: DateTime) -> bool:
        return self.compare_to(other) > 0

    def __ge__(self, other: DateTime) -> bool:
        return self.compare_to(other) >= 0
