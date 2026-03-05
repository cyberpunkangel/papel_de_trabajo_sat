"""Authenticate service translator.

Parses the SOAP authentication response to extract the Token, and builds
the SOAP request envelope for authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.sat.internal import xml_utils
from app.sat.shared.date_time import DateTime
from app.sat.shared.token import Token

if TYPE_CHECKING:
    from app.sat.request_builder.request_builder_interface import RequestBuilderInterface


class AuthenticateTranslator:
    """Translates SOAP authentication requests and responses."""

    def create_token_from_soap_response(self, content: str) -> Token:
        """Parse a SOAP authentication response and return a :class:`Token`.

        Args:
            content: The raw SOAP XML response body.

        Returns:
            A Token built from the ``Created``, ``Expires`` and
            ``AutenticaResult`` values found in the envelope.
        """
        env = xml_utils.read_xml_element(content)
        created_str = xml_utils.find_content(
            env, 'header', 'security', 'timestamp', 'created'
        )
        created = DateTime.create(created_str if created_str else 0)
        expires_str = xml_utils.find_content(
            env, 'header', 'security', 'timestamp', 'expires'
        )
        expires = DateTime.create(expires_str if expires_str else 0)
        value = xml_utils.find_content(
            env, 'body', 'autenticaResponse', 'autenticaResult'
        )
        return Token(created, expires, value)

    def create_soap_request(self, request_builder: RequestBuilderInterface) -> str:
        """Build the SOAP authentication request with default time window.

        Uses *now* as the ``since`` timestamp and *now + 5 minutes* as
        the ``until`` timestamp.

        Args:
            request_builder: The signed-request builder implementation.

        Returns:
            The signed SOAP XML envelope as a string.
        """
        since = DateTime.now()
        until = since.modify('+5 minutes')
        return self.create_soap_request_with_data(request_builder, since, until)

    def create_soap_request_with_data(
        self,
        request_builder: RequestBuilderInterface,
        since: DateTime,
        until: DateTime,
        security_token_id: str = '',
    ) -> str:
        """Build the SOAP authentication request with explicit time data.

        Args:
            request_builder: The signed-request builder implementation.
            since: Token creation timestamp.
            until: Token expiration timestamp.
            security_token_id: Optional security token identifier.

        Returns:
            The signed SOAP XML envelope as a string.
        """
        return request_builder.authorization(since, until, security_token_id)
