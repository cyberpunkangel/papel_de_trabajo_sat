"""Defines the service endpoints for SAT web service consumption."""

from __future__ import annotations

from app.sat.shared.enums import ServiceType


class ServiceEndpoints:
    """Contains the endpoints to consume the SAT web service.

    Use ``ServiceEndpoints.cfdi()`` for "CFDI regulares".
    Use ``ServiceEndpoints.retenciones()`` for "CFDI de retenciones e informacion de pagos".
    """

    def __init__(
        self,
        authenticate: str,
        query: str,
        verify: str,
        download: str,
        service_type: ServiceType,
    ) -> None:
        """Create a ServiceEndpoints instance.

        Args:
            authenticate: The authentication endpoint URL.
            query: The query (solicita descarga) endpoint URL.
            verify: The verify (verifica solicitud) endpoint URL.
            download: The download (descarga masiva) endpoint URL.
            service_type: The ServiceType for these endpoints.
        """
        self._authenticate: str = authenticate
        self._query: str = query
        self._verify: str = verify
        self._download: str = download
        self._service_type: ServiceType = service_type

    @classmethod
    def cfdi(cls) -> ServiceEndpoints:
        """Create an object with known endpoints for "CFDI regulares"."""
        return cls(
            'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc',
            'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/SolicitaDescargaService.svc',
            'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc',
            'https://cfdidescargamasiva.clouda.sat.gob.mx/DescargaMasivaService.svc',
            ServiceType.cfdi(),
        )

    @classmethod
    def retenciones(cls) -> ServiceEndpoints:
        """Create an object with known endpoints for "CFDI de retenciones e informacion de pagos"."""
        return cls(
            'https://retendescargamasivasolicitud.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc',
            'https://retendescargamasivasolicitud.clouda.sat.gob.mx/SolicitaDescargaService.svc',
            'https://retendescargamasivasolicitud.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc',
            'https://retendescargamasiva.clouda.sat.gob.mx/DescargaMasivaService.svc',
            ServiceType.retenciones(),
        )

    @property
    def authenticate(self) -> str:
        """The authentication endpoint URL."""
        return self._authenticate

    @property
    def query(self) -> str:
        """The query endpoint URL."""
        return self._query

    @property
    def verify(self) -> str:
        """The verify endpoint URL."""
        return self._verify

    @property
    def download(self) -> str:
        """The download endpoint URL."""
        return self._download

    @property
    def service_type(self) -> ServiceType:
        """The service type for these endpoints."""
        return self._service_type

    def get_authenticate(self) -> str:
        """The authentication endpoint URL."""
        return self._authenticate

    def get_query(self) -> str:
        """The query endpoint URL."""
        return self._query

    def get_verify(self) -> str:
        """The verify endpoint URL."""
        return self._verify

    def get_download(self) -> str:
        """The download endpoint URL."""
        return self._download

    def get_service_type(self) -> ServiceType:
        """The service type for these endpoints."""
        return self._service_type

    def __repr__(self) -> str:
        return f'ServiceEndpoints(service_type={self._service_type.value!r})'
