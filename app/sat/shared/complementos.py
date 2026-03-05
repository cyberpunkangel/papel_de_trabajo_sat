"""Complemento types for SAT web service CFDI and Retenciones queries."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants shared by all complemento types
# ---------------------------------------------------------------------------
UNDEFINED_KEY = 'undefined'
UNDEFINED_SAT_CODE = ''
UNDEFINED_LABEL = 'Sin complemento definido'


# ---------------------------------------------------------------------------
# ComplementoCfdi
# ---------------------------------------------------------------------------

class ComplementoCfdi(Enum):
    """Defines the complement type for consuming the "CFDI Regulares" service.

    Each member stores (sat_code, label) as its value tuple.
    """

    UNDEFINED = ('', 'Sin complemento definido')
    ACREDITAMIENTO_IEPS_10 = ('acreditamientoieps10', 'Acreditamiento del IEPS 1.0')
    AEROLINEAS_10 = ('aerolineas', 'Aerol\u00edneas 1.0')
    CARTAPORTE_10 = ('cartaporte10', 'Carta Porte 1.0')
    CARTAPORTE_20 = ('cartaporte20', 'Carta Porte 2.0')
    CERTIFICADO_DESTRUCCION_10 = ('certificadodedestruccion', 'Certificado de destrucci\u00f3n 1.0')
    CFDI_REGISTRO_FISCAL_10 = ('cfdiregistrofiscal', 'CFDI Registro fiscal 1.0')
    COMERCIO_EXTERIOR_10 = ('comercioexterior10', 'Comercio Exterior 1.0')
    COMERCIO_EXTERIOR_11 = ('comercioexterior11', 'Comercio Exterior 1.1')
    CONSUMO_COMBUSTIBLES_10 = ('consumodecombustibles', 'Consumo de combustibles 1.0')
    CONSUMO_COMBUSTIBLES_11 = ('consumodecombustibles11', 'Consumo de combustibles 1.1')
    DETALLISTA = ('detallista', 'Detallista')
    DIVISAS_10 = ('divisas', 'Divisas 1.0')
    DONATARIAS_11 = ('donat11', 'Donatarias 1.1')
    ESTADO_CUENTA_COMBUSTIBLES_11 = ('ecc11', 'Estado de cuenta de combustibles 1.1')
    ESTADO_CUENTA_COMBUSTIBLES_12 = ('ecc12', 'Estado de cuenta de combustibles 1.2')
    GASTOS_HIDROCARBUROS_10 = ('gastoshidrocarburos10', 'Gastos Hidrocarburos 1.0')
    INSTITUCIONES_EDUCATIVAS_PRIVADAS_10 = ('iedu', 'Instituciones educativas privadas 1.0')
    IMPUESTOS_LOCALES_10 = ('implocal', 'Impuestos locales 1.0')
    INE_11 = ('ine11', 'INE 1.1')
    INGRESOS_HIDROCARBUROS_10 = ('ingresoshidrocarburos', 'Ingresos Hidrocarburos 1.0')
    LEYENDAS_FISCALES_10 = ('leyendasfisc', 'Leyendas Fiscales 1.0')
    NOMINA_11 = ('nomina11', 'N\u00f3mina 1.1')
    NOMINA_12 = ('nomina12', 'N\u00f3mina 1.2')
    NOTARIOS_PUBLICOS_10 = ('notariospublicos', 'Notarios p\u00fablicos 1.0')
    OBRAS_ARTE_PLASTICAS_Y_ANTIGUEDADES_10 = ('obrasarteantiguedades', 'Obras de arte pl\u00e1sticas y antig\u00fcedades 1.0')
    PAGO_EN_ESPECIE_10 = ('pagoenespecie', 'Pago en especie 1.0')
    RECEPCION_PAGOS_10 = ('pagos10', 'Recepci\u00f3n de pagos 1.0')
    RECEPCION_PAGOS_20 = ('pagos20', 'Recepci\u00f3n de pagos 2.0')
    PERSONA_FISICA_INTEGRANTE_COORDINADO_10 = ('pfic', 'Persona f\u00edsica integrante de coordinado 1.0')
    RENOVACION_Y_SUSTITUCION_VEHICULOS_10 = ('renovacionysustitucionvehiculos', 'Renovaci\u00f3n y sustituci\u00f3n de veh\u00edculos 1.0')
    SERVICIOS_PARCIALES_CONSTRUCCION_10 = ('servicioparcialconstruccion', 'Servicios parciales de construcci\u00f3n 1.0')
    SPEI = ('spei', 'SPEI')
    TERCEROS_11 = ('terceros11', 'Terceros 1.1')
    TURISTA_PASAJERO_EXTRANJERO_10 = ('turistapasajeroextranjero', 'Turista pasajero extranjero 1.0')
    VALES_DESPENSA_10 = ('valesdedespensa', 'Vales de despensa 1.0')
    VEHICULO_USADO_10 = ('vehiculousado', 'Veh\u00edculo usado 1.0')
    VENTA_VEHICULOS_11 = ('ventavehiculos11', 'Venta de veh\u00edculos 1.1')

    def __init__(self, sat_code: str, label_text: str) -> None:
        self._sat_code = sat_code
        self._label = label_text

    def sat_code(self) -> str:
        """Return the SAT code for this complemento."""
        return self._sat_code

    def label(self) -> str:
        """Return the human-readable label for this complemento."""
        return self._label

    def is_undefined(self) -> bool:
        """Return True if this is the undefined (empty) complemento."""
        return self is ComplementoCfdi.UNDEFINED

    def json_serialize(self) -> str:
        """Return the SAT code for JSON serialization."""
        return self._sat_code

    @classmethod
    def undefined(cls) -> ComplementoCfdi:
        """Return the undefined complemento."""
        return cls.UNDEFINED

    @classmethod
    def create(cls, sat_code: str) -> ComplementoCfdi:
        """Find a complemento by its SAT code.

        Args:
            sat_code: The SAT code string to look up.

        Returns:
            The matching ComplementoCfdi member, or UNDEFINED if not found.
        """
        if sat_code == '' or sat_code is None:
            return cls.UNDEFINED
        for member in cls:
            if member._sat_code == sat_code:
                return member
        return cls.UNDEFINED

    @classmethod
    def get_labels(cls) -> Dict[str, str]:
        """Return a dictionary mapping SAT codes to labels."""
        return {member._sat_code: member._label for member in cls}


# ---------------------------------------------------------------------------
# ComplementoRetenciones
# ---------------------------------------------------------------------------

class ComplementoRetenciones(Enum):
    """Defines the complement type for consuming the "CFDI de retenciones e informacion de pagos" service.

    Each member stores (sat_code, label) as its value tuple.
    """

    UNDEFINED = ('', 'Sin complemento definido')
    ARRENDAMIENTO_EN_FIDEICOMISO = ('arrendamientoenfideicomiso', 'Arrendamiento en fideicomiso')
    DIVIDENDOS = ('dividendos', 'Dividendos')
    ENAJENACION_ACCIONES = ('enajenaciondeacciones', 'Enajenaci\u00f3n de acciones')
    FIDEICOMISO_NO_EMPRESARIAL = ('fideicomisonoempresarial', 'Fideicomiso no empresarial')
    INTERESES = ('intereses', 'Intereses')
    INTERESES_HIPOTECARIOS = ('intereseshipotecarios', 'Intereses hipotecarios')
    OPERACIONES_CON_DERIVADOS = ('operacionesconderivados', 'Operaciones con derivados')
    PAGOS_A_EXTRANJEROS = ('pagosaextranjeros', 'Pagos a extranjeros')
    PLANES_RETIRO_10 = ('planesderetiro', 'Planes de retiro 1.0')
    PLANES_RETIRO_11 = ('planesderetiro11', 'Planes de retiro 1.1')
    PREMIOS = ('premios', 'Premios')
    SECTOR_FINANCIERO = ('sectorfinanciero', 'Sector Financiero')
    SERVICIOS_PLATAFORMAS_TECNOLOGICAS = ('serviciosplataformastecnologicas10', 'Servicios Plataformas Tecnol\u00f3gicas')

    def __init__(self, sat_code: str, label_text: str) -> None:
        self._sat_code = sat_code
        self._label = label_text

    def sat_code(self) -> str:
        """Return the SAT code for this complemento."""
        return self._sat_code

    def label(self) -> str:
        """Return the human-readable label for this complemento."""
        return self._label

    def is_undefined(self) -> bool:
        """Return True if this is the undefined (empty) complemento."""
        return self is ComplementoRetenciones.UNDEFINED

    def json_serialize(self) -> str:
        """Return the SAT code for JSON serialization."""
        return self._sat_code

    @classmethod
    def undefined(cls) -> ComplementoRetenciones:
        """Return the undefined complemento."""
        return cls.UNDEFINED

    @classmethod
    def create(cls, sat_code: str) -> ComplementoRetenciones:
        """Find a complemento by its SAT code.

        Args:
            sat_code: The SAT code string to look up.

        Returns:
            The matching ComplementoRetenciones member, or UNDEFINED if not found.
        """
        if sat_code == '' or sat_code is None:
            return cls.UNDEFINED
        for member in cls:
            if member._sat_code == sat_code:
                return member
        return cls.UNDEFINED

    @classmethod
    def get_labels(cls) -> Dict[str, str]:
        """Return a dictionary mapping SAT codes to labels."""
        return {member._sat_code: member._label for member in cls}


# ---------------------------------------------------------------------------
# ComplementoUndefined
# ---------------------------------------------------------------------------

class ComplementoUndefined(Enum):
    """Defines the generic complement type. Only has the undefined member.

    Used when no specific complement service type applies.
    Each member stores (sat_code, label) as its value tuple.
    """

    UNDEFINED = ('', 'Sin complemento definido')

    def __init__(self, sat_code: str, label_text: str) -> None:
        self._sat_code = sat_code
        self._label = label_text

    def sat_code(self) -> str:
        """Return the SAT code for this complemento."""
        return self._sat_code

    def label(self) -> str:
        """Return the human-readable label for this complemento."""
        return self._label

    def is_undefined(self) -> bool:
        """Return True if this is the undefined (empty) complemento."""
        return self is ComplementoUndefined.UNDEFINED

    def json_serialize(self) -> str:
        """Return the SAT code for JSON serialization."""
        return self._sat_code

    @classmethod
    def undefined(cls) -> ComplementoUndefined:
        """Return the undefined complemento."""
        return cls.UNDEFINED

    @classmethod
    def create(cls, sat_code: str) -> ComplementoUndefined:
        """Find a complemento by its SAT code.

        Args:
            sat_code: The SAT code string to look up.

        Returns:
            The matching ComplementoUndefined member, or UNDEFINED if not found.
        """
        if sat_code == '' or sat_code is None:
            return cls.UNDEFINED
        for member in cls:
            if member._sat_code == sat_code:
                return member
        return cls.UNDEFINED

    @classmethod
    def get_labels(cls) -> Dict[str, str]:
        """Return a dictionary mapping SAT codes to labels."""
        return {member._sat_code: member._label for member in cls}
