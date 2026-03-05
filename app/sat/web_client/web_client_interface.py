"""Abstract interface to proxy an HTTP client.

Uses :mod:`abc` so that
concrete implementations must provide :meth:`call`, :meth:`fire_request`
and :meth:`fire_response`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.sat.web_client.request import Request
from app.sat.web_client.response import Response


class WebClientInterface(ABC):
    """Interface to proxy an HTTP client.

    See :class:`~app.sat.web_client.httpx_web_client.HttpxWebClient` for the
    default concrete implementation.
    """

    @abstractmethod
    async def call(self, request: Request) -> Response:
        """Make the HTTP call to the web service.

        This method should *not* call
        :meth:`fire_request` / :meth:`fire_response`.

        Raises:
            WebClientException: when an error is found.
        """
        ...

    @abstractmethod
    def fire_request(self, request: Request) -> None:
        """Hook called *before* calling the web service."""
        ...

    @abstractmethod
    def fire_response(self, response: Response) -> None:
        """Hook called *after* calling the web service."""
        ...
