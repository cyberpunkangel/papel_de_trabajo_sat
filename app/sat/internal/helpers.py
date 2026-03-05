"""Helper functions used by the library.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations

import re


def nospaces(text: str) -> str:
    """Remove horizontal whitespace at the beginning of each line and all line
    endings, effectively collapsing XML into a single line.

    After collapsing, the sequence ``?><`` is expanded back to ``?>\\n<`` so
    that the XML declaration stays on its own line.
    """
    # A: remove horizontal spaces at beginning of each line
    text = re.sub(r'^[ \t]*', '', text, flags=re.MULTILINE)
    # B: remove horizontal spaces + optional CR + LF
    text = re.sub(r'[ \t]*\r?\n', '', text, flags=re.MULTILINE)
    # C: xml definition on its own line
    text = text.replace('?><', '?>\n<')
    return text


def clean_pem_contents(pem: str) -> str:
    """Strip PEM header/footer lines and return just the base64 content
    without newlines.

    Any line starting with ``-----`` (e.g. ``-----BEGIN CERTIFICATE-----``)
    is removed.  The remaining lines are trimmed and joined together.
    """
    filtered = [
        line.strip()
        for line in pem.split('\n')
        if not line.startswith('-----')
    ]
    return ''.join(filtered)
