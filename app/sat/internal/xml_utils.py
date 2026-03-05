"""XML utility functions.

Provides helpers for parsing XML strings and navigating elements
using :mod:`lxml.etree`.  Element matching is always done by **local name**
(ignoring namespace prefixes), case-insensitive.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from lxml import etree


def read_xml_document(source: str) -> etree._ElementTree:
    """Parse an XML string and return the :class:`~lxml.etree._ElementTree`.

    Raises:
        ValueError: If *source* is empty.
    """
    if not source:
        raise ValueError('Cannot load an xml with empty content')
    parser = etree.XMLParser(huge_tree=True)
    root = etree.fromstring(source.encode('utf-8'), parser=parser)
    return root.getroottree()


def read_xml_element(source: str) -> etree._Element:
    """Parse an XML string and return the root :class:`~lxml.etree._Element`.

    Raises:
        ValueError: If *source* is empty or has no document element.
    """
    doc = read_xml_document(source)
    root = doc.getroot()
    if root is None:
        raise ValueError('Cannot load an xml without document element')
    return root


def _local_name(element: etree._Element) -> str:
    """Return the local name of an element, stripping any namespace."""
    tag = element.tag
    if isinstance(tag, str) and tag.startswith('{'):
        return tag.split('}', 1)[1]
    return str(tag)


def find_element(element: etree._Element, *names: str) -> Optional[etree._Element]:
    """Navigate nested XML children by local name (case-insensitive).

    Each entry in *names* represents a successive child to descend into.
    Returns ``None`` when any level is not found.
    """
    if not names:
        return element

    current = names[0].lower()
    remaining = names[1:]

    for child in element:
        if not isinstance(child.tag, str):
            continue
        if _local_name(child).lower() == current:
            if remaining:
                return find_element(child, *remaining)
            return child
    return None


def _extract_element_content(element: etree._Element) -> str:
    """Return the concatenated, trimmed direct text nodes of *element*."""
    parts: List[str] = []
    # element.text is the text before the first child
    if element.text:
        stripped = element.text.strip()
        if stripped:
            parts.append(stripped)
    # tail text after each child (still belongs to *element*)
    for child in element:
        if child.tail:
            stripped = child.tail.strip()
            if stripped:
                parts.append(stripped)
    return ''.join(parts)


def find_content(element: etree._Element, *names: str) -> str:
    """Find an element by the chain of *names* and return its text content.

    Returns an empty string when the element is not found.
    """
    found = find_element(element, *names)
    if found is None:
        return ''
    return _extract_element_content(found)


def find_elements(element: etree._Element, *names: str) -> List[etree._Element]:
    """Find all sibling elements whose local name matches the last entry in *names*.

    The preceding entries in *names* are used to navigate to a parent first.
    """
    if not names:
        return []

    names_list = list(names)
    target = names_list.pop().lower()

    if names_list:
        parent = find_element(element, *names_list)
    else:
        parent = element

    if parent is None:
        return []

    found: List[etree._Element] = []
    for child in parent:
        if not isinstance(child.tag, str):
            continue
        if _local_name(child).lower() == target:
            found.append(child)
    return found


def find_contents(element: etree._Element, *names: str) -> List[str]:
    """Return the text content of every element found by :func:`find_elements`."""
    return [_extract_element_content(el) for el in find_elements(element, *names)]


def find_attributes(element: etree._Element, *search: str) -> Dict[str, str]:
    """Find an element by the chain of *search* names and return its attributes.

    Attribute keys are returned in lowercase.  Returns an empty dict when the
    element is not found.
    """
    found = find_element(element, *search)
    if found is None:
        return {}

    attributes: Dict[str, str] = {}
    for attr_name, attr_value in found.attrib.items():
        # Strip namespace from attribute name if present
        if isinstance(attr_name, str) and attr_name.startswith('{'):
            local = attr_name.split('}', 1)[1]
        else:
            local = str(attr_name)
        attributes[local.lower()] = attr_value

    return attributes
