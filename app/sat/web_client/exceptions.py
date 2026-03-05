"""Exception hierarchy and SoapFaultInfo for the web client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from app.sat.web_client.request import Request
    from app.sat.web_client.response import Response


# ---------------------------------------------------------------------------
# SoapFaultInfo  (value object, NOT an exception)
# ---------------------------------------------------------------------------

class SoapFaultInfo:
    """Immutable container for a SOAP fault code and message."""

    def __init__(self, code: str, message: str) -> None:
        self._code = code
        self._message = message

    def get_code(self) -> str:
        return self._code

    def get_message(self) -> str:
        return self._message

    def __str__(self) -> str:
        return self._message

    def to_dict(self) -> Dict[str, str]:
        """Return a JSON-serialisable dictionary (replaces JsonSerializable)."""
        return {
            "code": self._code,
            "message": self._message,
        }

    def __repr__(self) -> str:
        return f"SoapFaultInfo(code={self._code!r}, message={self._message!r})"


# ---------------------------------------------------------------------------
# Exception hierarchy
#
#   RuntimeError
#     -> WebClientException
#          -> HttpClientError
#                -> SoapFaultError
#          -> HttpServerError
# ---------------------------------------------------------------------------

class WebClientException(RuntimeError):
    """Base exception raised by any :class:`WebClientInterface` implementation."""

    def __init__(
        self,
        message: str,
        request: Request,
        response: Response,
        previous: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self._request = request
        self._response = response
        self.__cause__ = previous

    def get_request(self) -> Request:
        return self._request

    def get_response(self) -> Response:
        return self._response


class HttpClientError(WebClientException):
    """Raised when the server replies with a 4xx status code."""


class HttpServerError(WebClientException):
    """Raised when the server replies with a 5xx status code."""


class SoapFaultError(HttpClientError):
    """Raised when a SOAP fault is detected in the response."""

    def __init__(
        self,
        request: Request,
        response: Response,
        fault: SoapFaultInfo,
        previous: Optional[BaseException] = None,
    ) -> None:
        message = f"Fault: {fault.get_code()} - {fault.get_message()}"
        super().__init__(message, request, response, previous)
        self._fault = fault

    def get_fault(self) -> SoapFaultInfo:
        return self._fault
