"""Query service: parameters, result, translator and validator.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from app.sat.internal import xml_utils
from app.sat.shared.complementos import (
    ComplementoCfdi,
    ComplementoRetenciones,
    ComplementoUndefined,
)
from app.sat.shared.date_time import DateTime
from app.sat.shared.date_time_period import DateTimePeriod
from app.sat.shared.enums import (
    DocumentStatus,
    DocumentType,
    DownloadType,
    RequestType,
    ServiceType,
)
from app.sat.shared.rfc_filter import RfcMatch, RfcMatches, RfcOnBehalf
from app.sat.shared.status_code import StatusCode
from app.sat.shared.uuid import Uuid

if TYPE_CHECKING:
    from app.sat.request_builder.request_builder_interface import RequestBuilderInterface


# ---------------------------------------------------------------------------
# QueryParameters
# ---------------------------------------------------------------------------

class QueryParameters:
    """Immutable container with all the information required to perform a
    query on the SAT Web Service.

    Use the ``create()`` factory and ``with_*()`` builder methods to
    construct instances.
    """

    def __init__(
        self,
        period: DateTimePeriod,
        download_type: DownloadType,
        request_type: RequestType,
        document_type: DocumentType,
        complement: Union[ComplementoCfdi, ComplementoRetenciones, ComplementoUndefined],
        document_status: DocumentStatus,
        uuid: Uuid,
        rfc_on_behalf: RfcOnBehalf,
        rfc_matches: RfcMatches,
        service_type: ServiceType,
    ) -> None:
        self._period = period
        self._download_type = download_type
        self._request_type = request_type
        self._document_type = document_type
        self._complement = complement
        self._document_status = document_status
        self._uuid = uuid
        self._rfc_on_behalf = rfc_on_behalf
        self._rfc_matches = rfc_matches
        self._service_type = service_type

    # -- Factory -----------------------------------------------------------

    @classmethod
    def create(
        cls,
        period: Optional[DateTimePeriod] = None,
        download_type: Optional[DownloadType] = None,
        request_type: Optional[RequestType] = None,
        service_type: Optional[ServiceType] = None,
    ) -> QueryParameters:
        """Create a QueryParameters with sensible defaults.

        Args:
            period: The time period. Defaults to [now, now + 1s].
            download_type: Defaults to ``DownloadType.issued()``.
            request_type: Defaults to ``RequestType.metadata()``.
            service_type: Defaults to ``ServiceType.cfdi()``.
        """
        current_time = int(time.time())
        return cls(
            period=period or DateTimePeriod.create_from_values(current_time, current_time + 1),
            download_type=download_type or DownloadType.issued(),
            request_type=request_type or RequestType.metadata(),
            document_type=DocumentType.undefined(),
            complement=ComplementoUndefined.undefined(),
            document_status=DocumentStatus.undefined(),
            uuid=Uuid.empty(),
            rfc_on_behalf=RfcOnBehalf.empty(),
            rfc_matches=RfcMatches.create(),
            service_type=service_type or ServiceType.cfdi(),
        )

    # -- Getters -----------------------------------------------------------

    def get_service_type(self) -> ServiceType:
        return self._service_type

    def get_period(self) -> DateTimePeriod:
        return self._period

    def get_download_type(self) -> DownloadType:
        return self._download_type

    def get_request_type(self) -> RequestType:
        return self._request_type

    def get_document_type(self) -> DocumentType:
        return self._document_type

    def get_complement(self) -> Union[ComplementoCfdi, ComplementoRetenciones, ComplementoUndefined]:
        return self._complement

    def get_document_status(self) -> DocumentStatus:
        return self._document_status

    def get_uuid(self) -> Uuid:
        return self._uuid

    def get_rfc_on_behalf(self) -> RfcOnBehalf:
        return self._rfc_on_behalf

    def get_rfc_matches(self) -> RfcMatches:
        return self._rfc_matches

    def get_rfc_match(self) -> RfcMatch:
        return self._rfc_matches.get_first()

    # -- Builder (with_*) --------------------------------------------------

    def _with(self, **overrides: Any) -> QueryParameters:
        """Return a new instance replacing only the specified fields."""
        defaults: Dict[str, Any] = {
            'period': self._period,
            'download_type': self._download_type,
            'request_type': self._request_type,
            'document_type': self._document_type,
            'complement': self._complement,
            'document_status': self._document_status,
            'uuid': self._uuid,
            'rfc_on_behalf': self._rfc_on_behalf,
            'rfc_matches': self._rfc_matches,
            'service_type': self._service_type,
        }
        defaults.update(overrides)
        return QueryParameters(**defaults)

    def with_service_type(self, service_type: ServiceType) -> QueryParameters:
        return self._with(service_type=service_type)

    def with_period(self, period: DateTimePeriod) -> QueryParameters:
        return self._with(period=period)

    def with_download_type(self, download_type: DownloadType) -> QueryParameters:
        return self._with(download_type=download_type)

    def with_request_type(self, request_type: RequestType) -> QueryParameters:
        return self._with(request_type=request_type)

    def with_document_type(self, document_type: DocumentType) -> QueryParameters:
        return self._with(document_type=document_type)

    def with_complement(
        self,
        complement: Union[ComplementoCfdi, ComplementoRetenciones, ComplementoUndefined],
    ) -> QueryParameters:
        return self._with(complement=complement)

    def with_document_status(self, document_status: DocumentStatus) -> QueryParameters:
        return self._with(document_status=document_status)

    def with_uuid(self, uuid: Uuid) -> QueryParameters:
        return self._with(uuid=uuid)

    def with_rfc_on_behalf(self, rfc_on_behalf: RfcOnBehalf) -> QueryParameters:
        return self._with(rfc_on_behalf=rfc_on_behalf)

    def with_rfc_matches(self, rfc_matches: RfcMatches) -> QueryParameters:
        return self._with(rfc_matches=rfc_matches)

    def with_rfc_match(self, rfc_match: RfcMatch) -> QueryParameters:
        return self._with(rfc_matches=RfcMatches.create(rfc_match))

    # -- Validation --------------------------------------------------------

    def validate(self) -> List[str]:
        """Return a list of validation error strings (empty if valid)."""
        validator = QueryValidator()
        return validator.validate(self)

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'serviceType': self._service_type.value,
            'period': self._period.to_dict(),
            'downloadType': self._download_type.value,
            'requestType': self._request_type.value,
            'documentType': self._document_type.value,
            'complement': self._complement.json_serialize(),
            'documentStatus': self._document_status.value,
            'uuid': self._uuid.to_dict(),
            'rfcOnBehalf': self._rfc_on_behalf.to_dict(),
            'rfcMatches': self._rfc_matches.to_dict(),
        }

    def __repr__(self) -> str:
        return (
            f'QueryParameters(service_type={self._service_type.value!r}, '
            f'download_type={self._download_type.value!r}, '
            f'request_type={self._request_type.value!r})'
        )


# ---------------------------------------------------------------------------
# QueryResult
# ---------------------------------------------------------------------------

class QueryResult:
    """Result of a query (SolicitaDescarga) operation.

    Contains the status code and, on success, the request identification
    required for the verification step.
    """

    def __init__(self, status: StatusCode, request_id: str) -> None:
        self._status = status
        self._request_id = request_id

    def get_status(self) -> StatusCode:
        """Status of the query call."""
        return self._status

    def get_request_id(self) -> str:
        """If accepted, the request identification for verification."""
        return self._request_id

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'status': self._status.to_dict(),
            'requestId': self._request_id,
        }

    def __repr__(self) -> str:
        return f'QueryResult(status={self._status!r}, request_id={self._request_id!r})'


# ---------------------------------------------------------------------------
# QueryTranslator
# ---------------------------------------------------------------------------

class QueryTranslator:
    """Translates between SOAP envelopes and :class:`QueryResult` objects."""

    def _resolve_response_path(self, envelope: Any) -> List[str]:
        """Determine the SOAP response path based on which element exists."""
        if xml_utils.find_element(envelope, 'body', 'solicitaDescargaEmitidosResponse') is not None:
            return ['body', 'solicitaDescargaEmitidosResponse', 'solicitaDescargaEmitidosResult']
        if xml_utils.find_element(envelope, 'body', 'solicitaDescargaRecibidosResponse') is not None:
            return ['body', 'solicitaDescargaRecibidosResponse', 'solicitaDescargaRecibidosResult']
        if xml_utils.find_element(envelope, 'body', 'SolicitaDescargaFolioResponse') is not None:
            return ['body', 'SolicitaDescargaFolioResponse', 'SolicitaDescargaFolioResult']
        return []

    def create_query_result_from_soap_response(self, content: str) -> QueryResult:
        """Parse a SOAP response into a :class:`QueryResult`.

        Args:
            content: The raw SOAP XML response body.

        Returns:
            A QueryResult with the parsed status code and request id.
        """
        env = xml_utils.read_xml_element(content)
        path = self._resolve_response_path(env)

        values = xml_utils.find_attributes(env, *path) if path else {}
        status = StatusCode(
            int(values.get('codestatus', '0') or '0'),
            str(values.get('mensaje', '') or ''),
        )
        request_id = str(values.get('idsolicitud', '') or '')
        return QueryResult(status, request_id)

    def create_soap_request(
        self,
        request_builder: RequestBuilderInterface,
        parameters: QueryParameters,
    ) -> str:
        """Build the signed SOAP request for a query operation.

        Args:
            request_builder: The signed-request builder implementation.
            parameters: The query parameters.

        Returns:
            The SOAP XML envelope as a string.
        """
        return request_builder.query(parameters)


# ---------------------------------------------------------------------------
# QueryValidator
# ---------------------------------------------------------------------------

class QueryValidator:
    """Validates :class:`QueryParameters` according to SAT business rules."""

    def validate(self, query: QueryParameters) -> List[str]:
        """Return a list of validation error messages.

        If the query is by UUID (folio), ``_validate_folio`` rules apply.
        Otherwise, ``_validate_query`` rules apply.

        Returns:
            An empty list when the parameters are valid.
        """
        if not query.get_uuid().is_empty():
            return self._validate_folio(query)
        return self._validate_query(query)

    def _validate_folio(self, query: QueryParameters) -> List[str]:
        errors: List[str] = []

        if not query.get_rfc_matches().is_empty():
            errors.append('En una consulta por UUID no se debe usar el filtro de RFC.')
        if not query.get_complement().is_undefined():
            errors.append('En una consulta por UUID no se debe usar el filtro de complemento.')
        if not query.get_document_status().is_undefined():
            errors.append('En una consulta por UUID no se debe usar el filtro de estado de documento.')
        if not query.get_document_type().is_undefined():
            errors.append('En una consulta por UUID no se debe usar el filtro de tipo de documento.')

        return errors

    def _validate_query(self, query: QueryParameters) -> List[str]:
        errors: List[str] = []

        period = query.get_period()
        if period.get_start() >= period.get_end():
            errors.append(
                f'La fecha de inicio ({period.get_start().format("%Y-%m-%d %H:%M:%S")}) '
                f'no puede ser mayor o igual a la fecha final '
                f'({period.get_end().format("%Y-%m-%d %H:%M:%S")}) del periodo de consulta.'
            )

        minimal_date = DateTime.now().modify('-6 years')
        if period.get_start() < minimal_date:
            errors.append(
                f'La fecha de inicio ({period.get_start().format("%Y-%m-%d %H:%M:%S")}) '
                f'no puede ser menor a hoy menos 6 anios atras '
                f'({minimal_date.format("%Y-%m-%d %H:%M:%S")}).'
            )

        if (
            query.get_download_type().is_received()
            and query.get_request_type().is_xml()
            and not query.get_document_status().is_active()
        ):
            errors.append(
                f'No es posible hacer una consulta de XML Recibidos que contenga Cancelados. '
                f'Solicitado: {query.get_document_status().get_query_attribute_value()}.'
            )

        if query.get_download_type().is_received() and query.get_rfc_matches().count() > 1:
            errors.append('No es posible hacer una consulta de Recibidos con mas de 1 RFC emisor.')

        if query.get_download_type().is_issued() and query.get_rfc_matches().count() > 5:
            errors.append('No es posible hacer una consulta de Emitidos con mas de 5 RFC receptores.')

        complement = query.get_complement()
        if (
            query.get_service_type().is_cfdi()
            and not complement.is_undefined()
            and not isinstance(complement, ComplementoCfdi)
        ):
            errors.append(
                f'El complemento de CFDI definido no es un complemento registrado '
                f'de este tipo ({complement.label()}).'
            )

        if (
            query.get_service_type().is_retenciones()
            and not complement.is_undefined()
            and not isinstance(complement, ComplementoRetenciones)
        ):
            errors.append(
                f'El complemento de Retenciones definido no es un complemento registrado '
                f'de este tipo ({complement.label()}).'
            )

        return errors
