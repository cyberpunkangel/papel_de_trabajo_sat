"""Main Service class for the SAT Web Service Descarga Masiva.

Provides the high-level async API: :meth:`authenticate`, :meth:`query`,
:meth:`verify`, and :meth:`download`.
"""

from __future__ import annotations

from typing import Optional

from app.sat.internal.service_consumer import ServiceConsumer
from app.sat.request_builder.request_builder_interface import RequestBuilderInterface
from app.sat.services.authenticate import AuthenticateTranslator
from app.sat.services.download import DownloadResult, DownloadTranslator
from app.sat.services.query import QueryParameters, QueryResult, QueryTranslator
from app.sat.services.verify import VerifyResult, VerifyTranslator
from app.sat.shared.service_endpoints import ServiceEndpoints
from app.sat.shared.token import Token
from app.sat.web_client.web_client_interface import WebClientInterface


class Service:
    """Main class to consume the SAT web service Descarga Masiva.

    All service methods are async. The recommended flow is:

    1. :meth:`authenticate` -- obtain a token.
    2. :meth:`query` -- submit a query request.
    3. :meth:`verify` -- poll until the query is finished.
    4. :meth:`download` -- download each package.
    """

    def __init__(
        self,
        request_builder: RequestBuilderInterface,
        web_client: WebClientInterface,
        token: Optional[Token] = None,
        endpoints: Optional[ServiceEndpoints] = None,
    ) -> None:
        """Create a Service instance.

        Args:
            request_builder: The signed-request builder implementation.
            web_client: The HTTP client abstraction.
            token: An optional pre-existing token. Defaults to an empty token.
            endpoints: Service endpoints. Defaults to CFDI endpoints.
        """
        self._request_builder = request_builder
        self._web_client = web_client
        self._token = token if token is not None else Token.empty()
        self._endpoints = endpoints if endpoints is not None else ServiceEndpoints.cfdi()

    # -- Token management --------------------------------------------------

    async def obtain_current_token(self) -> Token:
        """Return the current token, refreshing it if invalid or expired.

        This method reuses the current token when it is still valid.
        If there is no token or the current token has expired, it calls
        :meth:`authenticate` to obtain a new one.

        Returns:
            A valid Token.
        """
        if not self._token.is_valid():
            self._token = await self.authenticate()
        return self._token

    def get_token(self) -> Token:
        """Return the current token (may be invalid)."""
        return self._token

    def set_token(self, token: Token) -> None:
        """Replace the current token.

        Args:
            token: The new token.
        """
        self._token = token

    def get_endpoints(self) -> ServiceEndpoints:
        """Return the service endpoints."""
        return self._endpoints

    # -- Service operations ------------------------------------------------

    async def authenticate(self) -> Token:
        """Perform authentication and return a Token.

        The returned token might be invalid if the SAT service denies
        the request.

        Returns:
            A Token parsed from the SOAP response.
        """
        translator = AuthenticateTranslator()
        soap_body = translator.create_soap_request(self._request_builder)
        response_body = await self._consume(
            'http://DescargaMasivaTerceros.gob.mx/IAutenticacion/Autentica',
            self._endpoints.get_authenticate(),
            soap_body,
            None,  # do not use a token
        )
        return translator.create_token_from_soap_response(response_body)

    async def query(self, parameters: QueryParameters) -> QueryResult:
        """Submit a query (SolicitaDescarga) to the web service.

        If the endpoint's service type does not match the parameters'
        service type, the parameters are updated to match.

        Args:
            parameters: The query parameters.

        Returns:
            A QueryResult with the response status and request id.
        """
        if not self._endpoints.get_service_type().equal_to(parameters.get_service_type()):
            parameters = parameters.with_service_type(self._endpoints.get_service_type())

        translator = QueryTranslator()
        soap_body = translator.create_soap_request(self._request_builder, parameters)
        soap_action = self._resolve_soap_action(parameters)
        response_body = await self._consume(
            f'http://DescargaMasivaTerceros.sat.gob.mx/ISolicitaDescargaService/{soap_action}',
            self._endpoints.get_query(),
            soap_body,
            await self.obtain_current_token(),
        )
        return translator.create_query_result_from_soap_response(response_body)

    async def verify(self, request_id: str) -> VerifyResult:
        """Verify the status of a query (VerificaSolicitudDescarga).

        Args:
            request_id: The request identifier from a previous query.

        Returns:
            A VerifyResult with the query status and package ids.
        """
        translator = VerifyTranslator()
        soap_body = translator.create_soap_request(self._request_builder, request_id)
        response_body = await self._consume(
            'http://DescargaMasivaTerceros.sat.gob.mx/'
            'IVerificaSolicitudDescargaService/VerificaSolicitudDescarga',
            self._endpoints.get_verify(),
            soap_body,
            await self.obtain_current_token(),
        )
        return translator.create_verify_result_from_soap_response(response_body)

    async def download(self, package_id: str) -> DownloadResult:
        """Download a package (Descargar).

        Args:
            package_id: The package identifier to download.

        Returns:
            A DownloadResult with the status and package bytes.
        """
        translator = DownloadTranslator()
        soap_body = translator.create_soap_request(self._request_builder, package_id)
        response_body = await self._consume(
            'http://DescargaMasivaTerceros.sat.gob.mx/'
            'IDescargaMasivaTercerosService/Descargar',
            self._endpoints.get_download(),
            soap_body,
            await self.obtain_current_token(),
        )
        return translator.create_download_result_from_soap_response(response_body)

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_soap_action(parameters: QueryParameters) -> str:
        """Determine the SOAP action based on the query parameters.

        Returns:
            ``'SolicitaDescargaFolio'`` for UUID queries,
            ``'SolicitaDescargaRecibidos'``  for received queries, or
            ``'SolicitaDescargaEmitidos'`` for issued queries.
        """
        if not parameters.get_uuid().is_empty():
            return 'SolicitaDescargaFolio'
        if parameters.get_download_type().is_received():
            return 'SolicitaDescargaRecibidos'
        return 'SolicitaDescargaEmitidos'

    async def _consume(
        self,
        soap_action: str,
        uri: str,
        body: str,
        token: Optional[Token],
    ) -> str:
        """Execute a SOAP call via the :class:`ServiceConsumer`.

        Args:
            soap_action: The SOAPAction header value.
            uri: The endpoint URI.
            body: The SOAP XML body.
            token: The authentication token (or None for auth requests).

        Returns:
            The response body as a string.
        """
        return await ServiceConsumer.consume(
            self._web_client, soap_action, uri, body, token
        )
