"""httpx-based implementation of :class:`WebClientInterface`.

Built with :mod:`httpx` and its ``AsyncClient``. All HTTP calls are ``async``.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

import httpx

from app.sat.web_client.exceptions import WebClientException
from app.sat.web_client.request import Request
from app.sat.web_client.response import Response
from app.sat.web_client.web_client_interface import WebClientInterface


class HttpxWebClient(WebClientInterface):
    """WebClientInterface implementation based on ``httpx.AsyncClient``.

    You can inject two optional callables to observe requests and responses
    before and after the HTTP round-trip.

    Args:
        client: An existing :class:`httpx.AsyncClient` instance.  When
            ``None`` a new client is created on each call.
        on_fire_request: Called *before* making the HTTP call.
        on_fire_response: Called *after* making the HTTP call.
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        on_fire_request: Optional[Callable[[Request], None]] = None,
        on_fire_response: Optional[Callable[[Response], None]] = None,
    ) -> None:
        self._client = client
        self._on_fire_request = on_fire_request
        self._on_fire_response = on_fire_response

    # -- Hook methods --------------------------------------------------------

    def fire_request(self, request: Request) -> None:
        if self._on_fire_request is not None:
            self._on_fire_request(request)

    def fire_response(self, response: Response) -> None:
        if self._on_fire_response is not None:
            self._on_fire_response(response)

    # -- Core HTTP call ------------------------------------------------------

    async def call(self, request: Request) -> Response:
        """Perform the async HTTP request and return a :class:`Response`.

        Raises:
            WebClientException: wrapping the original ``httpx.HTTPError``
                when the request fails for any reason.
        """
        try:
            client = self._client or httpx.AsyncClient(
                timeout=httpx.Timeout(600.0, connect=30.0),
            )
            try:
                httpx_response = await client.request(
                    method=request.get_method(),
                    url=request.get_uri(),
                    headers=request.get_headers(),
                    content=request.get_body(),
                )
            finally:
                # If we created the client ourselves, close it
                if self._client is None:
                    await client.aclose()
        except httpx.HTTPError as exc:
            # Try to extract a partial response when available
            httpx_resp = getattr(exc, "response", None)
            response = self._create_response_from_httpx(httpx_resp)
            message = f"Error connecting to {request.get_uri()}"
            raise WebClientException(message, request, response, exc) from exc

        return self._create_response_from_httpx(httpx_response)

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _create_response_from_httpx(
        response: Optional[httpx.Response],
    ) -> Response:
        """Convert an :class:`httpx.Response` (or ``None``) to our
        :class:`Response` value object.

        When *response* is ``None`` (e.g. no response was received at all)
        a synthetic ``500`` response with an empty body is returned.
        """
        if response is None:
            return Response(500, "", {})

        body = response.text
        headers: Dict[str, str] = {
            k: v for k, v in response.headers.items()
        }
        return Response(response.status_code, body, headers)
