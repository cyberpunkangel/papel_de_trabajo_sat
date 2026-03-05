"""Defines a FIEL (Firma Electronica / eFirma) for SAT web services.
Uses the :mod:`cryptography` library for certificate and signing operations.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Optional, Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509.oid import NameOID, ObjectIdentifier

from app.sat.internal.helpers import clean_pem_contents


# OID 2.5.4.45 = x500UniqueIdentifier, used by SAT to embed the RFC
_OID_X500_UNIQUE_IDENTIFIER = ObjectIdentifier('2.5.4.45')


class Fiel:
    """Represents a FIEL credential (certificate + private key).

    Use the :meth:`create` static factory to build instances from raw
    PEM/DER bytes.
    """

    def __init__(
        self,
        certificate: x509.Certificate,
        private_key: PrivateKeyTypes,
    ) -> None:
        self._certificate = certificate
        self._private_key = private_key

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        cert_contents: bytes,
        key_contents: bytes,
        passphrase: str,
    ) -> Fiel:
        """Create a Fiel from raw certificate and private-key bytes.

        Both PEM and DER formats are accepted.  The private key is
        expected to be password-protected with *passphrase*.

        Args:
            cert_contents: Raw bytes of the certificate (PEM or DER).
            key_contents: Raw bytes of the private key (PEM or DER).
            passphrase: Password for the private key.

        Raises:
            ValueError: If loading fails for both PEM and DER.
        """
        password = passphrase.encode('utf-8') if passphrase else None

        # --- Load certificate (try PEM first, then DER) ---
        certificate: Optional[x509.Certificate] = None
        try:
            certificate = x509.load_pem_x509_certificate(cert_contents)
        except Exception:
            pass
        if certificate is None:
            try:
                certificate = x509.load_der_x509_certificate(cert_contents)
            except Exception as exc:
                raise ValueError('Unable to load the certificate in PEM or DER format') from exc

        # --- Load private key (try PEM first, then DER) ---
        private_key: Optional[PrivateKeyTypes] = None
        try:
            private_key = serialization.load_pem_private_key(key_contents, password=password)
        except Exception:
            pass
        if private_key is None:
            try:
                private_key = serialization.load_der_private_key(key_contents, password=password)
            except Exception as exc:
                raise ValueError('Unable to load the private key in PEM or DER format') from exc

        return Fiel(certificate, private_key)

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, data: str, algorithm: str = 'sha1') -> str:
        """Sign *data* using RSA-PKCS1v15 and return the raw signature bytes as
        a base64-encoded string.

        Args:
            data: The string to sign (encoded as UTF-8).
            algorithm: Hash algorithm name (``'sha1'`` by default).

        Returns:
            Base64-encoded signature.
        """
        hash_algo: hashes.HashAlgorithm
        if algorithm.lower() == 'sha1':
            hash_algo = hashes.SHA1()  # noqa: S303
        elif algorithm.lower() in ('sha256', 'sha-256'):
            hash_algo = hashes.SHA256()
        elif algorithm.lower() in ('sha384', 'sha-384'):
            hash_algo = hashes.SHA384()
        elif algorithm.lower() in ('sha512', 'sha-512'):
            hash_algo = hashes.SHA512()
        else:
            hash_algo = hashes.SHA1()  # noqa: S303

        if not isinstance(self._private_key, rsa.RSAPrivateKey):
            raise TypeError('Only RSA private keys are supported for signing')

        signature = self._private_key.sign(
            data.encode('utf-8'),
            padding.PKCS1v15(),
            hash_algo,
        )
        return base64.b64encode(signature).decode('ascii')

    def sign_bytes(self, data: str, algorithm: str = 'sha1') -> bytes:
        """Sign *data* and return the raw signature bytes (not base64).

        Returns raw bytes that the caller can base64-encode.
        """
        hash_algo: hashes.HashAlgorithm
        if algorithm.lower() == 'sha1':
            hash_algo = hashes.SHA1()  # noqa: S303
        elif algorithm.lower() in ('sha256', 'sha-256'):
            hash_algo = hashes.SHA256()
        else:
            hash_algo = hashes.SHA1()  # noqa: S303

        if not isinstance(self._private_key, rsa.RSAPrivateKey):
            raise TypeError('Only RSA private keys are supported for signing')

        return self._private_key.sign(
            data.encode('utf-8'),
            padding.PKCS1v15(),
            hash_algo,
        )

    # ------------------------------------------------------------------
    # Certificate queries
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        """Check the certificate is within its validity dates and is a FIEL type.

        The FIEL type is identified by:
        - The certificate must have the SAT x500UniqueIdentifier OID (2.5.4.45)
          in its subject.
        - The serial number pattern or key usage must match FIEL characteristics.

        For simplicity, this checks the validity period and that the subject
        contains the x500UniqueIdentifier attribute (which SAT FIEL certs have).
        """
        now = datetime.now(timezone.utc)
        if now < self._certificate.not_valid_before_utc:
            return False
        if now > self._certificate.not_valid_after_utc:
            return False

        # Check it is a FIEL-type certificate (has x500UniqueIdentifier in subject)
        try:
            attrs = self._certificate.subject.get_attributes_for_oid(_OID_X500_UNIQUE_IDENTIFIER)
            if not attrs:
                return False
        except Exception:
            return False

        return True

    def get_certificate_pem_contents(self) -> str:
        """Return the base64-encoded certificate content without PEM headers.
        """
        pem_bytes = self._certificate.public_bytes(serialization.Encoding.PEM)
        pem_str = pem_bytes.decode('ascii')
        return clean_pem_contents(pem_str)

    def get_rfc(self) -> str:
        """Extract the RFC from the certificate subject.

        The RFC is stored in OID 2.5.4.45 (x500UniqueIdentifier) with a value
        like ``" / XAXX010101000"`` -- the RFC is the part after the last ``/``.
        """
        try:
            attrs = self._certificate.subject.get_attributes_for_oid(_OID_X500_UNIQUE_IDENTIFIER)
            if not attrs:
                return ''
            raw_value = attrs[0].value
            if isinstance(raw_value, bytes):
                raw_value = raw_value.decode('utf-8', errors='replace')
            raw_value = str(raw_value)
            # Split on '/' and take the last non-empty segment, trimmed
            parts = raw_value.split('/')
            for part in reversed(parts):
                stripped = part.strip()
                if stripped:
                    return stripped
            return raw_value.strip()
        except Exception:
            return ''

    def get_certificate_serial(self) -> str:
        """Return the certificate serial number as a decimal string."""
        return str(self._certificate.serial_number)

    def get_certificate_issuer_name(self) -> str:
        """Return the certificate issuer in RFC 4514 string format."""
        return self._certificate.issuer.rfc4514_string()
