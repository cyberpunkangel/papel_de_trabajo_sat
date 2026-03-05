"""Procesador de CFDI de nómina para el generador de reportes."""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import List, Optional

from ..models.documento import Documento
from ..utils.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class NominasProcessor:
    """Procesa los XML de nómina dentro del directorio de descargas."""

    NOMINA_DIR_NAMES = [
        'RECIBOS_DE_NOMINA',
        'RECIBOS DE NOMINA',
        'RECIBOS_NOMINA',
        'NOMINA',
        'NOMINAS',
    ]

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.parser = XMLParser()

    def procesar(self) -> List[Documento]:
        archivos = self._collect_archivos()
        documentos: List[Documento] = []

        logger.info("Procesando %s archivos de nómina", len(archivos))

        for archivo in archivos:
            try:
                documento = self._procesar_archivo(archivo)
                if documento:
                    documentos.append(documento)
            except Exception as exc:  # pragma: no cover - logging de ayuda
                logger.exception("Error al procesar %s: %s", archivo, exc)

        logger.info("Se generaron %s registros de nómina", len(documentos))
        return documentos

    def _collect_archivos(self) -> List[str]:
        patrones = []
        for dirname in self.NOMINA_DIR_NAMES:
            patrones.append(self.data_root / dirname / '**' / '*.xml')
            patrones.append(self.data_root / '**' / dirname / '**' / '*.xml')

        archivos: List[str] = []
        vistos = set()
        for patron in patrones:
            for archivo in glob.glob(str(patron), recursive=True):
                ruta_normalizada = os.path.normcase(os.path.normpath(archivo))
                if ruta_normalizada not in vistos:
                    vistos.add(ruta_normalizada)
                    archivos.append(archivo)

        # Si no se detectó carpeta específica intenta con todos los XML del periodo
        if not archivos:
            patron_general = self.data_root / '**' / '*.xml'
            archivos = glob.glob(str(patron_general), recursive=True)

        return archivos

    def _procesar_archivo(self, archivo: str) -> Optional[Documento]:
        root, namespaces = self.parser.parse_file(archivo)

        if 'Comprobante' not in root.tag:
            return None

        if not self._tiene_complemento_nomina(root):
            return None

        emisor = root.find('.//{http://www.sat.gob.mx/cfd/4}Emisor')
        if emisor is None:
            emisor = root.find('.//{http://www.sat.gob.mx/cfd/3}Emisor')

        nombre = emisor.get('Nombre', 'No especificado') if emisor is not None else 'No especificado'
        rfc = emisor.get('Rfc', 'No especificado') if emisor is not None else 'No especificado'

        uuid = self.parser.get_uuid(root, namespaces)

        total_gravado, total_exento, isr_retenido = self._procesar_percepciones(root)
        if isr_retenido == 0.0:
            isr_retenido = self._procesar_deducciones(root)

        return Documento(
            tipo_ingreso='nomina12',
            nombre=nombre,
            rfc=rfc,
            uuid=uuid,
            ingreso_gravado=total_gravado,
            exentos=total_exento,
            isr_retenido=isr_retenido,
        )

    def _tiene_complemento_nomina(self, root):
        if root.find('.//{http://www.sat.gob.mx/nomina12}Nomina') is not None:
            return True
        for elem in root.iter():
            if 'nomina' in elem.tag.lower():
                return True
        return False

    def _procesar_percepciones(self, root):
        total_gravado = 0.0
        total_exento = 0.0
        isr_retenido = 0.0

        percepciones = root.find('.//{http://www.sat.gob.mx/nomina12}Percepciones')
        if percepciones is not None:
            for percepcion in percepciones.findall('{http://www.sat.gob.mx/nomina12}Percepcion'):
                if percepcion.get('TipoPercepcion') == '022':
                    gravado = self.parser.safe_float(percepcion.get('ImporteGravado'))
                    exento = self.parser.safe_float(percepcion.get('ImporteExento'))
                    isr_retenido += gravado + exento
                else:
                    total_gravado += self.parser.safe_float(percepcion.get('ImporteGravado'))
                    total_exento += self.parser.safe_float(percepcion.get('ImporteExento'))

        return total_gravado, total_exento, isr_retenido

    def _procesar_deducciones(self, root):
        isr_retenido = 0.0
        deducciones = root.find('.//{http://www.sat.gob.mx/nomina12}Deducciones')
        if deducciones is not None:
            for deduccion in deducciones.findall('{http://www.sat.gob.mx/nomina12}Deduccion'):
                concepto = deduccion.get('Concepto', '').lower()
                if deduccion.get('TipoDeduccion') == '002' or 'isr' in concepto or 'retenido' in concepto:
                    isr_retenido += self.parser.safe_float(deduccion.get('Importe'))
        return isr_retenido
