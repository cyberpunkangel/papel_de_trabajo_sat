"""Procesador de constancias de intereses para el reporte."""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import List, Optional

from ..models.documento import Documento
from ..utils.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class InteresesProcessor:
    """Procesa archivos de retenciones relacionados con intereses."""

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

        logger.info("Buscando intereses en %s archivos", len(archivos))

        for archivo in archivos:
            try:
                documento = self._procesar_archivo(archivo)
                if documento:
                    documentos.append(documento)
            except Exception as exc:  # pragma: no cover
                logger.exception("Error al procesar %s: %s", archivo, exc)

        logger.info("Se generaron %s registros de intereses", len(documentos))
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

        ns_list = [(k, v) for k, v in namespaces.items()]
        tipo_ingreso = self.parser.get_tipo_ingreso(ns_list)
        if tipo_ingreso in {'dividendos', 'enajenaciondeacciones', 'nomina12'}:
            return None

        intereses_elem = self._find_intereses_element(root, namespaces)
        if intereses_elem is None:
            return None

        tipo_ingreso = 'intereses'

        emisor = self._extraer_emisor(root, namespaces)
        nombre = emisor.get('NomDenRazSocE', 'No especificado')
        rfc = emisor.get('RfcE', 'No especificado')

        uuid = self.parser.get_uuid(root, namespaces)
        perdida = self._extraer_perdida(root, namespaces)
        totales_data = self._extraer_totales(root, namespaces)
        intereses_nom, intereses_real = self._extraer_intereses(root, namespaces, intereses_elem)

        return Documento(
            tipo_ingreso=tipo_ingreso or 'intereses',
            nombre=nombre,
            rfc=rfc,
            uuid=uuid,
            perdida=perdida,
            isr_retenido=totales_data.get('isr_retenido', 0.0),
            intereses_nominales=intereses_nom,
            intereses_reales=intereses_real,
        )

    def _extraer_emisor(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if 'retencion' in prefix.lower():
                emisor = root.find(f'.//{{{uri}}}Emisor')
                if emisor is not None:
                    return emisor
        return root

    def _extraer_perdida(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if 'interes' in prefix.lower():
                intereses = root.find(f'.//{{{uri}}}Intereses')
                if intereses is not None and 'Perdida' in intereses.attrib:
                    return self.parser.safe_float(intereses.get('Perdida'))
        return 0.0

    def _extraer_totales(self, root, namespaces):
        resultado = {'isr_retenido': 0.0}
        totales, totales_ns = self._find_totales_element(root, namespaces)
        if totales is None:
            return resultado

        monto_tot_ret = totales.get('MontoTotRet')
        if monto_tot_ret:
            resultado['isr_retenido'] = self.parser.safe_float(monto_tot_ret)

        if resultado['isr_retenido'] == 0 and totales_ns:
            for imp_ret in totales.findall(f'.//{{{totales_ns}}}ImpRetenidos'):
                resultado['isr_retenido'] = self.parser.safe_float(imp_ret.get('MontoRet'))
                if resultado['isr_retenido'] != 0:
                    break

        return resultado

    def _extraer_intereses(self, root, namespaces, intereses_elem):
        intereses_nominales = self.parser.safe_float(intereses_elem.get('MontIntNominal'))
        retiro_aores = intereses_elem.get('RetiroAORESRetInt', '').upper() == 'SI'

        if retiro_aores:
            totales, _ = self._find_totales_element(root, namespaces)
            intereses_reales = self.parser.safe_float(totales.get('MontoTotGrav')) if totales is not None else 0.0
        else:
            intereses_reales = self.parser.safe_float(intereses_elem.get('MontIntReal'))

        return intereses_nominales, intereses_reales

    def _find_intereses_element(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if not prefix or 'interes' not in prefix.lower():
                continue
            intereses_elem = root.find(f'.//{{{uri}}}Intereses')
            if intereses_elem is not None:
                return intereses_elem
        return None

    def _find_totales_element(self, root, namespaces):
        for prefix, uri in namespaces.items():
            if not prefix or 'retencion' not in prefix.lower():
                continue
            totales = root.find(f'.//{{{uri}}}Totales')
            if totales is not None:
                return totales, uri
        return None, None
