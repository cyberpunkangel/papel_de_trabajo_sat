"""Service consumer that executes SOAP calls via a web client.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from app.sat.internal import soap_fault_extractor
from app.sat.web_client.exceptions import (
    HttpClientError,
    HttpServerError,
    SoapFaultError,
    WebClientException,
)
from app.sat.web_client.request import Request

if TYPE_CHECKING:
    from app.sat.web_client.response import Response
    from app.sat.web_client.web_client_interface import WebClientInterface


class ServiceConsumer:
    """Executes SOAP calls, inspecting responses for faults and HTTP errors."""

    @staticmethod
    async def consume(
        web_client: WebClientInterface,
        soap_action: str,
        uri: str,
        body: str,
        token: Optional[object] = None,
    ) -> str:
        """Convenience static method that delegates to :meth:`execute`."""
        return await ServiceConsumer().execute(web_client, soap_action, uri, body, token)

    async def execute(
        self,
        web_client: WebClientInterface,
        soap_action: str,
        uri: str,
        body: str,
        token: Optional[object] = None,
    ) -> str:
        """Create a SOAP request, call the web service, and validate the response.

        Args:
            web_client: The HTTP client abstraction.
            soap_action: The SOAPAction header value.
            uri: The endpoint URI.
            body: The SOAP XML body.
            token: An optional token object with a ``get_value()`` method.

        Returns:
            The response body as a string.

        Raises:
            SoapFaultError: When a SOAP fault is found in the response.
            HttpClientError: When the response has a 4xx status.
            HttpServerError: When the response has a 5xx status or is empty.
        """
        headers = self.create_headers(soap_action, token)
        request = self.create_request(uri, body, headers)

        exception: Optional[BaseException] = None
        try:
            response = await self.run_request(web_client, request)
        except WebClientException as exc:
            exception = exc
            response = exc.get_response()

        self.check_errors(request, response, exception)
        return response.get_body()

    def create_request(self, uri: str, body: str, headers: Dict[str, str]) -> Request:
        """Build a POST :class:`~app.sat.web_client.request.Request`."""
        return Request('POST', uri, body, headers)

    def create_headers(self, soap_action: str, token: Optional[object] = None) -> Dict[str, str]:
        """Build the headers dict including SOAPAction and optional Authorization."""
        headers: Dict[str, str] = {'SOAPAction': soap_action}
        if token is not None:
            # Token has get_value() method
            token_value = token.get_value()  # type: ignore[attr-defined]
            headers['Authorization'] = f'WRAP access_token="{token_value}"'
        return headers

    async def run_request(
        self,
        web_client: WebClientInterface,
        request: Request,
    ) -> Response:
        """Fire hooks around the actual HTTP call."""
        web_client.fire_request(request)
        try:
            response = await web_client.call(request)
        except WebClientException as exc:
            web_client.fire_response(exc.get_response())
            raise
        web_client.fire_response(response)
        return response

    def check_errors(
        self,
        request: Request,
        response: Response,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Inspect the response for SOAP faults and HTTP error codes.

        Raises:
            SoapFaultError: If a SOAP fault is detected.
            HttpClientError: If the HTTP status is 4xx.
            HttpServerError: If the HTTP status is 5xx or the body is empty.
        """
        # Evaluate SoapFaultInfo
        fault = soap_fault_extractor.extract(response.get_body())
        if fault is not None:
            raise SoapFaultError(request, response, fault, exception)

        # Evaluate response status
        if response.status_code_is_client_error():
            message = f'Unexpected client error status code {response.get_status_code()}'
            raise HttpClientError(message, request, response, exception)

        if response.status_code_is_server_error():
            message = f'Unexpected server error status code {response.get_status_code()}'
            raise HttpServerError(message, request, response, exception)

        if response.is_empty():
            raise HttpServerError('Unexpected empty response from server', request, response, exception)
