"""
Manages FIEL certificate configuration.
"""

import json
import os
import shutil
import time
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.backends import default_backend

# Project root: two levels up from this file (app/config/fiel_config.py -> project root)
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'fiel_config.json')
FIEL_DIR = os.path.join(BASE_DIR, 'fiel-uploads')


class FielConfig:
    """Static methods class for FIEL certificate management."""

    @staticmethod
    def load() -> Optional[dict]:
        """Load configuration from JSON file."""
        if not os.path.isfile(CONFIG_FILE):
            return None

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save(config: dict) -> bool:
        """Save configuration to JSON file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except (OSError, TypeError, ValueError):
            return False

    @staticmethod
    def verify() -> bool:
        """Check that the configured certificate and key files exist on disk."""
        config = FielConfig.load()
        if not config:
            return False

        cert_exists = (
            'certificate_path' in config
            and os.path.isfile(config['certificate_path'])
        )
        key_exists = (
            'key_path' in config
            and os.path.isfile(config['key_path'])
        )

        return cert_exists and key_exists

    @staticmethod
    def validate_certificates(
        cert_path: str,
        key_path: str,
        password: str,
    ) -> dict:
        """
        Validate FIEL certificates and extract metadata.

        Uses the ``cryptography`` library to load the X.509 certificate and
        private key, verify they match, and return RFC, legal name, serial
        number, validity dates and issuer information.
        """
        if not os.path.isfile(cert_path):
            raise FileNotFoundError("El archivo de certificado no existe")

        if not os.path.isfile(key_path):
            raise FileNotFoundError("El archivo de llave no existe")

        # Read raw bytes
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        with open(key_path, 'rb') as f:
            key_data = f.read()

        password_bytes = password.encode('utf-8') if password else None

        try:
            # Load certificate (try PEM first, then DER)
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except Exception:
                cert = x509.load_der_x509_certificate(cert_data, default_backend())

            # Load private key (try PEM first, then DER)
            try:
                private_key = serialization.load_pem_private_key(
                    key_data, password=password_bytes, backend=default_backend(),
                )
            except Exception:
                private_key = serialization.load_der_private_key(
                    key_data, password=password_bytes, backend=default_backend(),
                )

            # Verify certificate and key match
            pub_cert = cert.public_key()
            pub_key = private_key.public_key()

            cert_pub_bytes = pub_cert.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            key_pub_bytes = pub_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            if cert_pub_bytes != key_pub_bytes:
                raise Exception("El certificado y la llave privada no coinciden")

            # Extract subject fields
            subject = cert.subject
            rfc = ''
            nombre = ''

            # SAT certificates store RFC in serialNumber or x500UniqueIdentifier
            for attr in subject:
                oid_dotted = attr.oid.dotted_string
                # OID 2.5.4.5 = serialNumber (RFC in SAT certs)
                if oid_dotted == '2.5.4.5':
                    raw = attr.value.strip()
                    # SAT serial‑number field: " / XAXX010101000"
                    if '/' in raw:
                        rfc = raw.split('/')[-1].strip()
                    else:
                        rfc = raw

            # Common Name or Organization for legal name
            try:
                cn_attrs = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
                if cn_attrs:
                    nombre = cn_attrs[0].value
            except Exception:
                pass

            if not nombre:
                try:
                    org_attrs = subject.get_attributes_for_oid(x509.oid.NameOID.ORGANIZATION_NAME)
                    if org_attrs:
                        nombre = org_attrs[0].value
                except Exception:
                    pass

            # Serial number of the certificate
            serial_number = str(cert.serial_number)

            # Validity dates
            valido_desde = cert.not_valid_before_utc.strftime('%Y-%m-%d')
            valido_hasta = cert.not_valid_after_utc.strftime('%Y-%m-%d')

            # Issuer as RFC4514 string
            emisor = cert.issuer.rfc4514_string()

            return {
                'rfc': rfc,
                'nombre': nombre,
                'valido_desde': valido_desde,
                'valido_hasta': valido_hasta,
                'serial': serial_number,
                'emisor': emisor,
            }

        except FileNotFoundError:
            raise
        except Exception as e:
            message = str(e)
            if 'password' in message.lower() or 'decrypt' in message.lower():
                raise Exception("Contrasena incorrecta") from e
            raise Exception(f"Error al validar certificados: {message}") from e

    @staticmethod
    def copy_files(cert_path: str, key_path: str) -> dict:
        """
        Copy uploaded certificate files into ``fiel-uploads/`` with a
        timestamp prefix.  Returns a dict with the new absolute paths.
        """
        os.makedirs(FIEL_DIR, exist_ok=True)

        timestamp = int(time.time())
        cert_filename = f"certificado_{timestamp}.cer"
        key_filename = f"llave_{timestamp}.key"

        cert_dest = os.path.join(FIEL_DIR, cert_filename)
        key_dest = os.path.join(FIEL_DIR, key_filename)

        try:
            shutil.copy2(cert_path, cert_dest)
        except OSError as e:
            raise Exception("No se pudo copiar el certificado") from e

        try:
            shutil.copy2(key_path, key_dest)
        except OSError as e:
            # Roll back certificate copy on failure
            if os.path.isfile(cert_dest):
                os.remove(cert_dest)
            raise Exception("No se pudo copiar la llave privada") from e

        return {
            'certificate_path': os.path.realpath(cert_dest),
            'key_path': os.path.realpath(key_dest),
        }

    @staticmethod
    def clean_old_files() -> None:
        """Remove previously configured certificate files from disk."""
        config = FielConfig.load()
        if config:
            cert = config.get('certificate_path', '')
            if cert and os.path.isfile(cert):
                os.remove(cert)

            key = config.get('key_path', '')
            if key and os.path.isfile(key):
                os.remove(key)
