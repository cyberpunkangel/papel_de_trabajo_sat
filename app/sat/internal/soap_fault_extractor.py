"""Extract SOAP fault information from an XML response.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

from typing import Optional

from app.sat.internal.xml_utils import find_element, read_xml_element
from app.sat.web_client.exceptions import SoapFaultInfo


def extract(source: str) -> Optional[SoapFaultInfo]:
    """Attempt to extract a SOAP fault from the XML *source*.

    Returns a :class:`~app.sat.web_client.exceptions.SoapFaultInfo` when a
    fault is found in ``body > fault > faultcode / faultstring``, or ``None``
    otherwise (including when *source* is not valid XML).
    """
    try:
        env = read_xml_element(source)
    except Exception:
        return None

    fault_code_el = find_element(env, 'body', 'fault', 'faultcode')
    fault_string_el = find_element(env, 'body', 'fault', 'faultstring')

    code = ''
    message = ''

    if fault_code_el is not None and fault_code_el.text:
        code = fault_code_el.text.strip()
    if fault_string_el is not None and fault_string_el.text:
        message = fault_string_el.text.strip()

    if not code and not message:
        return None

    return SoapFaultInfo(code, message)
