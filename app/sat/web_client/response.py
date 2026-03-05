"""Minimal representation of an HTTP response object."""

from __future__ import annotations

from typing import Dict


class Response:
    """Minimal representation of an HTTP response object."""

    def __init__(
        self,
        status_code: int,
        body: str,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self._status_code = status_code
        self._body = body
        self._headers: Dict[str, str] = headers if headers is not None else {}

    # -- Accessors -----------------------------------------------------------

    def get_status_code(self) -> int:
        return self._status_code

    def get_body(self) -> str:
        return self._body

    def get_headers(self) -> Dict[str, str]:
        return dict(self._headers)

    # -- Convenience helpers -------------------------------------------------

    def is_empty(self) -> bool:
        return self._body == ""

    def status_code_is_client_error(self) -> bool:
        """Return ``True`` when the status code is in the 400-499 range."""
        return 400 <= self._status_code < 500

    def status_code_is_server_error(self) -> bool:
        """Return ``True`` when the status code is in the 500-599 range."""
        return 500 <= self._status_code < 600

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable dictionary (replaces JsonSerializable)."""
        return {
            "status_code": self._status_code,
            "body": self._body,
            "headers": dict(self._headers),
        }

    def __repr__(self) -> str:
        return (
            f"Response(status_code={self._status_code!r}, "
            f"body={self._body[:60]!r}{'...' if len(self._body) > 60 else ''}, "
            f"headers={self._headers!r})"
        )
