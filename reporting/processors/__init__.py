"""Colección de procesadores de documentos XML del SAT."""

from .nominas import NominasProcessor
from .intereses import InteresesProcessor
from .dividendos import DividendosProcessor
from .enajenacion import EnajenacionProcessor
from .deducciones import DeduccionesProcessor

__all__ = [
    'NominasProcessor',
    'InteresesProcessor',
    'DividendosProcessor',
    'EnajenacionProcessor',
    'DeduccionesProcessor',
]
