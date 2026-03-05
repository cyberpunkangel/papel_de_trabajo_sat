"""Metadata preprocessor for SAT CSV files.

Fixes known issues in metadata text files from the SAT download service,
such as improper line endings.

This module is internal, do not use it outside this project.
"""

from __future__ import annotations


CONTROL_CR = '\r'
CONTROL_LF = '\n'
CONTROL_CRLF = '\r\n'


class MetadataPreprocessor:
    """Preprocesses SAT metadata CSV contents to fix known issues.

    The main issue addressed is that SAT CSV files use ``\\r\\n`` as the
    end-of-line marker but may contain bare ``\\n`` characters inside field
    values.  The :meth:`fix` method removes those stray newlines.
    """

    def __init__(self, contents: str) -> None:
        """Create a MetadataPreprocessor.

        Args:
            contents: The raw metadata CSV text.
        """
        self._contents = contents

    def get_contents(self) -> str:
        """Return the (possibly fixed) contents."""
        return self._contents

    def fix(self) -> None:
        """Apply all known fixes to the contents."""
        self.fix_eol_crlf()

    def fix_eol_crlf(self) -> None:
        """Fix inner ``\\n`` characters when EOL is ``\\r\\n``.

        If the file uses ``\\r\\n`` as line endings, any bare ``\\n``
        inside a field value is removed, and the final line endings are
        normalised to ``\\n`` only.
        """
        first_lf = self._contents.find(CONTROL_LF)
        if first_lf == -1:
            # No LF at all -- nothing to do
            return

        # Check if EOL is CR+LF
        eol_is_crlf = (
            first_lf > 0
            and self._contents[first_lf - 1:first_lf] == CONTROL_CR
        )

        if not eol_is_crlf:
            return

        # Split on proper CRLF boundaries, remove inner LFs, rejoin with LF
        lines = self._contents.split(CONTROL_CRLF)
        lines = [line.replace(CONTROL_LF, '') for line in lines]
        self._contents = CONTROL_LF.join(lines)
