"""Verify service: result and translator.
"""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

from app.sat.internal import xml_utils
from app.sat.shared.code_request import CodeRequest
from app.sat.shared.status_code import StatusCode
from app.sat.shared.status_request import StatusRequest

if TYPE_CHECKING:
    from app.sat.request_builder.request_builder_interface import RequestBuilderInterface


# ---------------------------------------------------------------------------
# VerifyResult
# ---------------------------------------------------------------------------

class VerifyResult:
    """Result of a verify (VerificaSolicitudDescarga) operation.

    Contains the overall status, the request status, the code request,
    the number of CFDIs, and the list of package identifiers.
    """

    def __init__(
        self,
        status: StatusCode,
        status_request: StatusRequest,
        code_request: CodeRequest,
        number_cfdis: int,
        *packages_ids: str,
    ) -> None:
        self._status = status
        self._status_request = status_request
        self._code_request = code_request
        self._number_cfdis = number_cfdis
        self._packages_ids: List[str] = list(packages_ids)

    def get_status(self) -> StatusCode:
        """Status of the verification call."""
        return self._status

    def get_status_request(self) -> StatusRequest:
        """Status of the query."""
        return self._status_request

    def get_code_request(self) -> CodeRequest:
        """Code related to the status of the query."""
        return self._code_request

    def get_number_cfdis(self) -> int:
        """Number of CFDI given by the query."""
        return self._number_cfdis

    def get_packages_ids(self) -> List[str]:
        """Package identifications required for the download process."""
        return list(self._packages_ids)

    def count_packages(self) -> int:
        """Count of package identifications."""
        return len(self._packages_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'status': self._status.to_dict(),
            'codeRequest': self._code_request.to_dict(),
            'statusRequest': self._status_request.to_dict(),
            'numberCfdis': self._number_cfdis,
            'packagesIds': self._packages_ids,
        }

    def __repr__(self) -> str:
        return (
            f'VerifyResult(status={self._status!r}, '
            f'status_request={self._status_request!r}, '
            f'packages={len(self._packages_ids)})'
        )


# ---------------------------------------------------------------------------
# VerifyTranslator
# ---------------------------------------------------------------------------

class VerifyTranslator:
    """Translates between SOAP envelopes and :class:`VerifyResult` objects."""

    def create_verify_result_from_soap_response(self, content: str) -> VerifyResult:
        """Parse a SOAP verify response into a :class:`VerifyResult`.

        Args:
            content: The raw SOAP XML response body.

        Returns:
            A VerifyResult with the parsed fields.
        """
        env = xml_utils.read_xml_element(content)

        values = xml_utils.find_attributes(
            env,
            'body',
            'VerificaSolicitudDescargaResponse',
            'VerificaSolicitudDescargaResult',
        )
        status = StatusCode(
            int(values.get('codestatus', '0') or '0'),
            str(values.get('mensaje', '') or ''),
        )
        status_request = StatusRequest(int(values.get('estadosolicitud', '0') or '0'))
        code_request = CodeRequest(int(values.get('codigoestadosolicitud', '0') or '0'))
        number_cfdis = int(values.get('numerocfdis', '0') or '0')

        packages = xml_utils.find_contents(
            env,
            'body',
            'VerificaSolicitudDescargaResponse',
            'VerificaSolicitudDescargaResult',
            'IdsPaquetes',
        )

        return VerifyResult(status, status_request, code_request, number_cfdis, *packages)

    def create_soap_request(
        self,
        request_builder: RequestBuilderInterface,
        request_id: str,
    ) -> str:
        """Build the signed SOAP request for a verify operation.

        Args:
            request_builder: The signed-request builder implementation.
            request_id: The request identifier to verify.

        Returns:
            The SOAP XML envelope as a string.
        """
        return request_builder.verify(request_id)
