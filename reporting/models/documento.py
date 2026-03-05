"""
Modelos de datos para documentos del SAT utilizados por el generador de reportes.
"""

from dataclasses import dataclass


@dataclass
class Documento:
    """Representa un documento del SAT ya procesado."""

    tipo_ingreso: str
    nombre: str
    rfc: str
    uuid: str
    ingreso_gravado: float = 0.0
    exentos: float = 0.0
    perdida: float = 0.0
    isr_retenido: float = 0.0
    intereses_nominales: float = 0.0
    intereses_reales: float = 0.0
    monto_dividendos_nacionales: float = 0.0
    monto_dividendos_extranjeros: float = 0.0
    isr_acreditable_mexico: float = 0.0
    isr_acreditable_extranjero: float = 0.0
    base_retencion: float = 0.0
    monto_retencion: float = 0.0
    uso_cfdi: str = ''
    monto_deducible: float = 0.0

    def to_dict(self) -> dict:
        """Convierte el documento a diccionario listo para pandas."""
        return {
            'TIPO DE INGRESO': self.tipo_ingreso,
            'NOMBRE': self.nombre,
            'RFC': self.rfc,
            'INGRESO GRAVADO': self.ingreso_gravado,
            'EXENTOS': self.exentos,
            'PERDIDA': self.perdida,
            'ISR RETENIDO': self.isr_retenido,
            'UUID': self.uuid,
            'INTERESES NOMINALES': self.intereses_nominales,
            'INTERESES REALES': self.intereses_reales,
            'MONTO DIVIDENDOS NACIONALES': self.monto_dividendos_nacionales,
            'MONTO DIVIDENDOS EXTRANJEROS': self.monto_dividendos_extranjeros,
            'ISR ACREDITABLE MÉXICO': self.isr_acreditable_mexico,
            'ISR ACREDITABLE EXTRANJERO': self.isr_acreditable_extranjero,
            'BASE DE LA RETENCIÓN': self.base_retencion,
            'MONTO RETENCIÓN': self.monto_retencion,
            'USO CFDI': self.uso_cfdi,
            'MONTO DEDUCIBLE': self.monto_deducible,
        }
