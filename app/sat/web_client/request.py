"""Minimal representation of an HTTP request object."""

from __future__ import annotations

from typing import Dict


class Request:
    """Minimal representation of an HTTP request object.

    Merges user-provided headers with default headers. Any header set to an
    empty string in *headers* will be removed from the final set (mirroring
    an ``array_filter``-style behavior on the merged array).
    """

    def __init__(
        self,
        method: str,
        uri: str,
        body: str,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self._method = method
        self._uri = uri
        self._body = body

        merged = {**self.default_headers(), **(headers or {})}
        # Filter out empty values
        self._headers: Dict[str, str] = {
            k: v for k, v in merged.items() if v
        }

    # -- Accessors -----------------------------------------------------------

    def get_method(self) -> str:
        return self._method

    def get_uri(self) -> str:
        return self._uri

    def get_body(self) -> str:
        return self._body

    def get_headers(self) -> Dict[str, str]:
        return dict(self._headers)

    # -- Default headers -----------------------------------------------------

    @staticmethod
    def default_headers() -> Dict[str, str]:
        """Default headers used on every request."""
        return {
            "Content-type": 'text/xml; charset="utf-8"',
            "Accept": "text/xml",
            "Cache-Control": "no-cache",
        }

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable dictionary (replaces JsonSerializable)."""
        return {
            "method": self._method,
            "uri": self._uri,
            "body": self._body,
            "headers": dict(self._headers),
        }

    def __repr__(self) -> str:
        return (
            f"Request(method={self._method!r}, uri={self._uri!r}, "
            f"body={self._body[:60]!r}{'...' if len(self._body) > 60 else ''}, "
            f"headers={self._headers!r})"
        )
