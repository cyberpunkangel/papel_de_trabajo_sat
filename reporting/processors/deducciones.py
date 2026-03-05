"""Procesador de deducciones personales desde CFDI recibidos."""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import List, Optional

from ..config import OTROS_CFDI_DIR_NAMES
from ..models.documento import Documento
from ..utils.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class DeduccionesProcessor:
    """Identifica CFDI deducibles para la hoja de deducciones personales."""

    USOS_CFDI_DEDUCCIONES = {
        'D01',
        'D02',
        'D03',
        'D04',
        'D05',
        'D06',
        'D07',
        'D08',
        'D09',
        'D10',
    }

    FORMAS_PAGO_NO_DEDUCIBLES = {
        '01',  # Efectivo
    }

    def __init__(self, data_root: Path, receptor_rfc: str = ''):
        self.data_root = Path(data_root)
        self.parser = XMLParser()
        self.receptor_rfc = (receptor_rfc or '').strip().upper()

    def procesar(self) -> List[Documento]:
        archivos = self._collect_archivos()
        documentos: List[Documento] = []

        logger.info("Buscando deducciones personales en %s archivos", len(archivos))

        for archivo in archivos:
            try:
                documento = self._procesar_archivo(archivo)
                if documento:
                    documentos.append(documento)
            except Exception as exc:  # pragma: no cover - logging de ayuda
                logger.exception("Error al procesar deducción %s: %s", archivo, exc)

        logger.info("Se generaron %s registros de deducciones", len(documentos))
        return documentos

    def _collect_archivos(self) -> List[str]:
        archivos: List[str] = []
        vistos = set()

        for dirname in OTROS_CFDI_DIR_NAMES:
            patterns = [
                self.data_root / dirname / '**' / '*.xml',
                self.data_root / '**' / dirname / '**' / '*.xml',
            ]
            for pattern in patterns:
                for archivo in glob.glob(str(pattern), recursive=True):
                    ruta_normalizada = os.path.normcase(os.path.normpath(archivo))
                    if ruta_normalizada not in vistos:
                        vistos.add(ruta_normalizada)
                        archivos.append(archivo)

        return archivos

    def _procesar_archivo(self, archivo: str) -> Optional[Documento]:
        root, namespaces = self.parser.parse_file(archivo)

        if 'Comprobante' not in root.tag:
            return None

        if self._tiene_complemento_nomina(root):
            return None

        tipo_comprobante = (root.get('TipoDeComprobante') or '').strip().upper()
        if tipo_comprobante and tipo_comprobante != 'I':
            return None

        emisor = root.find('.//{http://www.sat.gob.mx/cfd/4}Emisor')
        if emisor is None:
            emisor = root.find('.//{http://www.sat.gob.mx/cfd/3}Emisor')

        receptor = root.find('.//{http://www.sat.gob.mx/cfd/4}Receptor')
        if receptor is None:
            receptor = root.find('.//{http://www.sat.gob.mx/cfd/3}Receptor')

        if emisor is None:
            return None

        rfc_emisor = (emisor.get('Rfc') or '').strip().upper()
        nombre_emisor = (emisor.get('Nombre') or 'No especificado').strip() or 'No especificado'
        uso_cfdi = (receptor.get('UsoCFDI') if receptor is not None else '') or ''
        uso_cfdi = uso_cfdi.strip().upper()

        rfc_receptor = (receptor.get('Rfc') if receptor is not None else '') or ''
        rfc_receptor = rfc_receptor.strip().upper()
        forma_pago = (root.get('FormaPago') or '').strip().upper()

        if not self._es_deduccion_aceptada(uso_cfdi, forma_pago, rfc_receptor):
            return None

        total = self.parser.safe_float(root.get('Total'))
        if total <= 0:
            total = self.parser.safe_float(root.get('SubTotal'))
        if total <= 0:
            return None

        uuid = self.parser.get_uuid(root, namespaces)

        return Documento(
            tipo_ingreso='deducciones_personales',
            nombre=nombre_emisor,
            rfc=rfc_emisor or 'No especificado',
            uuid=uuid,
            uso_cfdi=uso_cfdi,
            monto_deducible=total,
        )

    def _es_deduccion_aceptada(
        self,
        uso_cfdi: str,
        forma_pago: str,
        rfc_receptor: str,
    ) -> bool:
        if uso_cfdi not in self.USOS_CFDI_DEDUCCIONES:
            return False

        if forma_pago in self.FORMAS_PAGO_NO_DEDUCIBLES:
            return False

        if self.receptor_rfc and rfc_receptor and rfc_receptor != self.receptor_rfc:
            return False

        return True

    def _tiene_complemento_nomina(self, root) -> bool:
        if root.find('.//{http://www.sat.gob.mx/nomina12}Nomina') is not None:
            return True
        for elem in root.iter():
            if 'nomina' in elem.tag.lower():
                return True
        return False
