"""Utilidades para parsear archivos XML del SAT."""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class XMLParser:
    """Parser simple para CFDI y retenciones."""

    NAMESPACES = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'cfdi3': 'http://www.sat.gob.mx/cfd/3',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        'nomina12': 'http://www.sat.gob.mx/nomina12',
        'retenciones': 'http://www.sat.gob.mx/esquemas/retencionpago/2',
        'retenciones1': 'http://www.sat.gob.mx/esquemas/retencionpago/1',
        'dividendos': 'http://www.sat.gob.mx/esquemas/retencionpago/1/dividendos',
        'intereses': 'http://www.sat.gob.mx/esquemas/retencionpago/1/intereses',
        'enajenaciondeacciones': 'http://www.sat.gob.mx/esquemas/retencionpago/1/enajenaciondeacciones',
    }

    @staticmethod
    def parse_file(filepath: str) -> Tuple[ET.Element, Dict[str, str]]:
        namespaces = {}
        for _, elem in ET.iterparse(filepath, events=('start-ns',)):
            prefix, uri = elem
            if prefix:
                namespaces[prefix] = uri

        tree = ET.parse(filepath)
        root = tree.getroot()
        merged = {**XMLParser.NAMESPACES, **namespaces}
        return root, merged

    @staticmethod
    def get_uuid(root: ET.Element, namespaces: Dict[str, str]) -> str:
        for ns_key in ['tfd', 'TimbreFiscalDigital']:
            if ns_key in namespaces:
                tfd = root.find(f'.//{{{namespaces[ns_key]}}}TimbreFiscalDigital')
                if tfd is not None and 'UUID' in tfd.attrib:
                    return tfd.get('UUID')
        for elem in root.iter():
            if 'TimbreFiscalDigital' in elem.tag and 'UUID' in elem.attrib:
                return elem.get('UUID')
        return 'No encontrado'

    @staticmethod
    def get_tipo_ingreso(namespaces: List[Tuple[str, str]]) -> str:
        omitir = {'xsi', 'tfd', 'retenciones', 'retenciones1', 'xs', 'schemaLocation'}
        for prefix, _ in namespaces:
            if prefix and prefix.lower() not in omitir:
                return prefix.lower()
        return 'desconocido'

    @staticmethod
    def safe_float(value: Optional[str], default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):  # pragma: no cover - defensivo
            return default
