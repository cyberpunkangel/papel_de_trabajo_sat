"""Procesador de enajenación de acciones para el reporte."""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import List, Optional, Set

from ..models.documento import Documento
from ..utils.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class EnajenacionProcessor:
    """Localiza CFDI de retenciones con complemento de enajenación."""

    RETENCIONES_DIR_NAMES = [
        'CONSTANCIAS_DE_RETENCIONES',
        'CONSTANCIAS DE RETENCIONES',
        'INTERESES, DIVIDENDOS, ENAJENACION DE ACCIONES',
        'RETENCIONES',
    ]

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.parser = XMLParser()

    def procesar(self) -> List[Documento]:
        archivos = self._collect_archivos()
        documentos: List[Documento] = []
        uuids: Set[str] = set()

        logger.info("Buscando enajenación en %s archivos", len(archivos))

        for archivo in archivos:
            try:
                documento = self._procesar_archivo(archivo)
                if documento and documento.uuid not in uuids:
                    documentos.append(documento)
                    uuids.add(documento.uuid)
            except Exception as exc:  # pragma: no cover
                logger.exception("Error al procesar %s: %s", archivo, exc)

        logger.info("Se generaron %s registros de enajenación", len(documentos))
        return documentos

    def _collect_archivos(self) -> List[str]:
        archivos: List[str] = []
        vistos = set()

        for dirname in self.RETENCIONES_DIR_NAMES:
            patron = self.data_root / dirname / '**' / '*.xml'
            for archivo in glob.glob(str(patron), recursive=True):
                ruta_normalizada = os.path.normcase(os.path.normpath(archivo))
                if ruta_normalizada not in vistos:
                    vistos.add(ruta_normalizada)
                    archivos.append(archivo)

        # Busqueda general para no dejar fuera archivos sueltos
        patron_general = self.data_root / '**' / '*.xml'
        for archivo in glob.glob(str(patron_general), recursive=True):
            ruta_normalizada = os.path.normcase(os.path.normpath(archivo))
            if ruta_normalizada not in vistos:
                vistos.add(ruta_normalizada)
                archivos.append(archivo)

        return archivos

    def _procesar_archivo(self, archivo: str) -> Optional[Documento]:
        root, namespaces = self.parser.parse_file(archivo)

        if 'Retenciones' not in root.tag:
            return None

        complemento = root.find('.//{*}Complemento')
        if complemento is None:
            return None

        es_enajenacion = False
        for child in complemento:
            if 'EnajenacionAcciones' in child.tag or 'enajenaciondeacciones' in child.tag.lower():
                es_enajenacion = True
                break
        if not es_enajenacion:
            return None

        emisor = root.find('.//{*}Emisor')
        if emisor is None:
            return None

        nombre = emisor.get('NomDenRazSocE', 'No especificado')
        rfc = emisor.get('RfcE', 'No especificado')
        uuid = self.parser.get_uuid(root, namespaces)
        montos = self._extraer_montos(root, namespaces)

        return Documento(
            tipo_ingreso='enajenaciondeacciones',
            nombre=nombre,
            rfc=rfc,
            uuid=uuid,
            ingreso_gravado=montos.get('gravado', 0.0),
            exentos=montos.get('exento', 0.0),
            perdida=montos.get('perdida', 0.0),
            isr_retenido=montos.get('retenido', 0.0),
        )

    def _extraer_montos(self, root, namespaces):
        resultado = {
            'gravado': 0.0,
            'exento': 0.0,
            'perdida': 0.0,
            'retenido': 0.0,
        }

        totales = root.find('.//{*}Totales')
        if totales is None:
            for prefix, uri in namespaces.items():
                totales = root.find(f'.//{{{uri}}}Totales')
                if totales is not None:
                    break

        if totales is not None:
            resultado['gravado'] = self.parser.safe_float(totales.get('MontoTotGrav'))
            resultado['exento'] = self.parser.safe_float(totales.get('MontoTotExent'))
            resultado['retenido'] = self.parser.safe_float(totales.get('MontoTotRet'))

        return resultado
