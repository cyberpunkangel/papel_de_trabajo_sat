"""SAT web service enums: DocumentType, DocumentStatus, DownloadType, RequestType, ServiceType."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class DocumentType(Enum):
    """Defines the document type for CFDI queries.

    Each member maps to its SAT query value.
    """

    UNDEFINED = ''
    INGRESO = 'I'
    EGRESO = 'E'
    TRASLADO = 'T'
    NOMINA = 'N'
    PAGO = 'P'

    def is_undefined(self) -> bool:
        return self is DocumentType.UNDEFINED

    def is_ingreso(self) -> bool:
        return self is DocumentType.INGRESO

    def is_egreso(self) -> bool:
        return self is DocumentType.EGRESO

    def is_traslado(self) -> bool:
        return self is DocumentType.TRASLADO

    def is_nomina(self) -> bool:
        return self is DocumentType.NOMINA

    def is_pago(self) -> bool:
        return self is DocumentType.PAGO

    def json_serialize(self) -> str:
        """Return the value for JSON serialization."""
        return self.value

    @classmethod
    def undefined(cls) -> DocumentType:
        return cls.UNDEFINED

    @classmethod
    def ingreso(cls) -> DocumentType:
        return cls.INGRESO

    @classmethod
    def egreso(cls) -> DocumentType:
        return cls.EGRESO

    @classmethod
    def traslado(cls) -> DocumentType:
        return cls.TRASLADO

    @classmethod
    def nomina(cls) -> DocumentType:
        return cls.NOMINA

    @classmethod
    def pago(cls) -> DocumentType:
        return cls.PAGO


class DocumentStatus(Enum):
    """Defines the document status for CFDI queries.

    Each member maps to its SAT query value.
    """

    UNDEFINED = ''
    ACTIVE = '1'
    CANCELLED = '0'

    def is_undefined(self) -> bool:
        return self is DocumentStatus.UNDEFINED

    def is_active(self) -> bool:
        return self is DocumentStatus.ACTIVE

    def is_cancelled(self) -> bool:
        return self is DocumentStatus.CANCELLED

    def get_query_attribute_value(self) -> str:
        """Return the SAT query attribute value for this status.

        Returns:
            'Todos' for undefined, 'Vigente' for active, 'Cancelado' for cancelled.
        """
        if self.is_undefined():
            return 'Todos'
        if self.is_active():
            return 'Vigente'
        if self.is_cancelled():
            return 'Cancelado'
        raise LogicError('Impossible case')

    def json_serialize(self) -> str:
        """Return the value for JSON serialization."""
        return self.value

    @classmethod
    def undefined(cls) -> DocumentStatus:
        return cls.UNDEFINED

    @classmethod
    def active(cls) -> DocumentStatus:
        return cls.ACTIVE

    @classmethod
    def cancelled(cls) -> DocumentStatus:
        return cls.CANCELLED


class DownloadType(Enum):
    """Defines the download type (issued or received).

    Each member maps to its SAT query value.
    """

    ISSUED = 'RfcEmisor'
    RECEIVED = 'RfcReceptor'

    def is_issued(self) -> bool:
        return self is DownloadType.ISSUED

    def is_received(self) -> bool:
        return self is DownloadType.RECEIVED

    def json_serialize(self) -> str:
        """Return the value for JSON serialization."""
        return self.value

    @classmethod
    def issued(cls) -> DownloadType:
        return cls.ISSUED

    @classmethod
    def received(cls) -> DownloadType:
        return cls.RECEIVED


class ServiceType(Enum):
    """Defines the service type (cfdi or retenciones).

    Uses the enum member name as the value (matching the project enum convention
    where no overrideValues is provided).
    """

    CFDI = 'cfdi'
    RETENCIONES = 'retenciones'

    def is_cfdi(self) -> bool:
        return self is ServiceType.CFDI

    def is_retenciones(self) -> bool:
        return self is ServiceType.RETENCIONES

    def equal_to(self, service_type: ServiceType) -> bool:
        """Check equality with another ServiceType."""
        return self.value == service_type.value

    def json_serialize(self) -> str:
        """Return the value for JSON serialization."""
        return self.value

    @classmethod
    def cfdi(cls) -> ServiceType:
        return cls.CFDI

    @classmethod
    def retenciones(cls) -> ServiceType:
        return cls.RETENCIONES


class RequestType(Enum):
    """Defines the request type (xml or metadata).

    Uses the enum member name as the value (matching the project enum convention
    where no overrideValues is provided).
    """

    XML = 'xml'
    METADATA = 'metadata'

    def is_xml(self) -> bool:
        return self is RequestType.XML

    def is_metadata(self) -> bool:
        return self is RequestType.METADATA

    def get_query_attribute_value(self, service_type: ServiceType) -> str:
        """Return the SAT query attribute value for this request type.

        Args:
            service_type: The service type (currently unused but kept for API compatibility).

        Returns:
            'CFDI' for xml, 'Metadata' for metadata.
        """
        return 'CFDI' if self.is_xml() else 'Metadata'

    def json_serialize(self) -> str:
        """Return the value for JSON serialization."""
        return self.value

    @classmethod
    def xml(cls) -> RequestType:
        return cls.XML

    @classmethod
    def metadata(cls) -> RequestType:
        return cls.METADATA
