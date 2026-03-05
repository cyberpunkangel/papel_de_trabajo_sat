"""Procesador de dividendos para el reporte."""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import List, Optional

from ..models.documento import Documento
from ..utils.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class DividendosProcessor:
    """Identifica y procesa constancias de dividendos."""

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

        logger.info("Buscando dividendos en %s archivos", len(archivos))

        for archivo in archivos:
            try:
                documento = self._procesar_archivo(archivo)
                if documento:
                    documentos.append(documento)
            except Exception as exc:  # pragma: no cover
                logger.exception("Error al procesar %s: %s", archivo, exc)

        logger.info("Se generaron %s registros de dividendos", len(documentos))
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

        if not archivos:
            patron_general = self.data_root / '**' / '*.xml'
            archivos = glob.glob(str(patron_general), recursive=True)

        return archivos

    def _procesar_archivo(self, archivo: str) -> Optional[Documento]:
        root, namespaces = self.parser.parse_file(archivo)

        if 'Retenciones' not in root.tag:
            return None

        dividendos_elem, _ = self._find_dividendos_element(root, namespaces)
        if dividendos_elem is None:
            return None

        emisor = self._extraer_emisor(root, namespaces)
        nombre = emisor.get('NomDenRazSocE', 'No especificado')
        rfc = emisor.get('RfcE', 'No especificado')

        uuid = self.parser.get_uuid(root, namespaces)
        dividendos_data = self._extraer_dividendos(dividendos_elem)
        base_ret, monto_ret = self._extraer_retencion(root, namespaces)

        return Documento(
            tipo_ingreso='dividendos',
            nombre=nombre,
            rfc=rfc,
            uuid=uuid,
            monto_dividendos_nacionales=dividendos_data.get('nacionales', 0.0),
            monto_dividendos_extranjeros=dividendos_data.get('extranjeros', 0.0),
            isr_acreditable_mexico=dividendos_data.get('isr_mexico', 0.0),
            isr_acreditable_extranjero=dividendos_data.get('isr_extranjero', 0.0),
            base_retencion=base_ret,
            monto_retencion=monto_ret,
        )

    def _extraer_emisor(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if 'retencion' in prefix.lower():
                emisor = root.find(f'.//{{{uri}}}Emisor')
                if emisor is not None:
                    return emisor
        return root

    def _find_dividendos_element(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if not prefix or 'dividend' not in prefix.lower():
                continue
            divid_util = root.find(f'.//{{{uri}}}DividOUtil')
            if divid_util is not None:
                return divid_util, uri
        return None, None

    def _extraer_dividendos(self, divid_util):
        resultado = {
            'nacionales': 0.0,
            'extranjeros': 0.0,
            'isr_mexico': 0.0,
            'isr_extranjero': 0.0,
        }
        resultado['nacionales'] = self.parser.safe_float(divid_util.get('MontDivAcumNal'))
        resultado['extranjeros'] = self.parser.safe_float(divid_util.get('MontDivAcumExt'))
        resultado['isr_mexico'] = self.parser.safe_float(divid_util.get('MontISRAcredRetMexico'))
        resultado['isr_extranjero'] = self.parser.safe_float(divid_util.get('MontISRAcredRetExtranjero'))
        return resultado

    def _extraer_retencion(self, root, namespaces):
        base_retencion = 0.0
        monto_retencion = 0.0
        for prefix, uri in namespaces.items():
            if 'retencion' in prefix.lower():
                totales = root.find(f'.//{{{uri}}}Totales')
                if totales is None:
                    continue
                for imp_ret in totales.findall(f'.//{{{uri}}}ImpRetenidos'):
                    if imp_ret.get('ImpuestoRet') in {'01', '001'}:
                        base_retencion = self.parser.safe_float(imp_ret.get('BaseRet'))
                        monto_retencion = self.parser.safe_float(imp_ret.get('MontoRet'))
                        if base_retencion or monto_retencion:
                            return base_retencion, monto_retencion
        return base_retencion, monto_retencion
