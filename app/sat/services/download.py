"""Download service: result and translator.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, TYPE_CHECKING

from app.sat.internal import xml_utils
from app.sat.shared.status_code import StatusCode

if TYPE_CHECKING:
    from app.sat.request_builder.request_builder_interface import RequestBuilderInterface


# ---------------------------------------------------------------------------
# DownloadResult
# ---------------------------------------------------------------------------

class DownloadResult:
    """Result of a download (Descargar) operation.

    Contains the status code and, on success, the raw package content
    (typically a ZIP file).
    """

    def __init__(self, status: StatusCode, package_content: bytes) -> None:
        """Create a DownloadResult.

        Args:
            status: The status of the download call.
            package_content: The raw bytes of the downloaded package.
        """
        self._status = status
        self._package_content = package_content
        self._package_size = len(package_content)

    def get_status(self) -> StatusCode:
        """Status of the download call."""
        return self._status

    def get_package_content(self) -> bytes:
        """The raw package contents (typically a ZIP file)."""
        return self._package_content

    def get_package_size(self) -> int:
        """Size of the package contents in bytes."""
        return self._package_size

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation for JSON serialization."""
        return {
            'status': self._status.to_dict(),
            'size': self._package_size,
        }

    def __repr__(self) -> str:
        return f'DownloadResult(status={self._status!r}, size={self._package_size})'


# ---------------------------------------------------------------------------
# DownloadTranslator
# ---------------------------------------------------------------------------

class DownloadTranslator:
    """Translates between SOAP envelopes and :class:`DownloadResult` objects."""

    def create_download_result_from_soap_response(self, content: str) -> DownloadResult:
        """Parse a SOAP download response into a :class:`DownloadResult`.

        The package content is base64-decoded from the ``Paquete`` element.

        Args:
            content: The raw SOAP XML response body.

        Returns:
            A DownloadResult with the parsed status and decoded package.
        """
        env = xml_utils.read_xml_element(content)
        values = xml_utils.find_attributes(env, 'header', 'respuesta')
        status = StatusCode(
            int(values.get('codestatus', '0') or '0'),
            str(values.get('mensaje', '') or ''),
        )
        package_b64 = xml_utils.find_content(
            env, 'body', 'RespuestaDescargaMasivaTercerosSalida', 'Paquete'
        )
        try:
            package_bytes = base64.b64decode(package_b64) if package_b64 else b''
        except Exception:
            package_bytes = b''
        return DownloadResult(status, package_bytes)

    def create_soap_request(
        self,
        request_builder: RequestBuilderInterface,
        package_id: str,
    ) -> str:
        """Build the signed SOAP request for a download operation.

        Args:
            request_builder: The signed-request builder implementation.
            package_id: The package identifier to download.

        Returns:
            The SOAP XML envelope as a string.
        """
        return request_builder.download(package_id)
