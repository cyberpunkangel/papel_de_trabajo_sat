"""Abstract interface for request builders.

Implementations must create signed XML messages ready to send to the
SAT Web Service Descarga Masiva.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.sat.shared.date_time import DateTime


class RequestBuilderInterface(ABC):
    """The implementors must create the request signed ready to send to the
    SAT Web Service Descarga Masiva.

    Information about owner (RFC, certificate, private key, etc.) is
    outside the scope of this interface.
    """

    @abstractmethod
    def authorization(self, created: DateTime, expires: DateTime, token_id: str = '') -> str:
        """Create an authorization signed XML message.

        Args:
            created: Timestamp of token creation.
            expires: Timestamp of token expiration.
            token_id: If empty, the implementation will create one.

        Returns:
            The signed XML envelope as a string.
        """
        ...

    @abstractmethod
    def query(self, params: object) -> str:
        """Create a query signed XML message.

        Args:
            params: A ``QueryParameters`` instance.

        Returns:
            The signed XML envelope as a string.
        """
        ...

    @abstractmethod
    def verify(self, request_id: str) -> str:
        """Create a verify signed XML message.

        Args:
            request_id: The request ID to verify.

        Returns:
            The signed XML envelope as a string.
        """
        ...

    @abstractmethod
    def download(self, package_id: str) -> str:
        """Create a download signed XML message.

        Args:
            package_id: The package ID to download.

        Returns:
            The signed XML envelope as a string.
        """
        ...
