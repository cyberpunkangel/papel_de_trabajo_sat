"""FIEL-based request builder for SAT web service SOAP envelopes.

Builds XML-DSIG signed SOAP envelopes for authentication, query,
verify and download operations against the SAT Descarga Masiva service.
"""

from __future__ import annotations

import base64
import hashlib
import uuid as _uuid
from typing import Any, Dict

from app.sat.internal.helpers import clean_pem_contents, nospaces
from app.sat.request_builder.fiel import Fiel
from app.sat.request_builder.request_builder_interface import RequestBuilderInterface


class FielRequestBuilder(RequestBuilderInterface):
    """Provides XML-DSIG signed SOAP envelopes using a :class:`Fiel` credential."""

    def __init__(self, fiel: Fiel) -> None:
        self._fiel = fiel

    def get_fiel(self) -> Fiel:
        return self._fiel

    # ------------------------------------------------------------------
    # RequestBuilderInterface
    # ------------------------------------------------------------------

    def authorization(self, created: Any, expires: Any, token_id: str = '') -> str:
        uuid = token_id if token_id else self._create_xml_security_token_id()
        certificate = clean_pem_contents(self._fiel.get_certificate_pem_contents())

        key_info_data = (
            f'<KeyInfo>'
            f'<o:SecurityTokenReference>'
            f'<o:Reference URI="#{uuid}" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>'
            f'</o:SecurityTokenReference>'
            f'</KeyInfo>'
        )

        to_digest_xml = (
            f'<u:Timestamp xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" u:Id="_0">'
            f'<u:Created>{created.format_sat()}</u:Created>'
            f'<u:Expires>{expires.format_sat()}</u:Expires>'
            f'</u:Timestamp>'
        )

        signature_data = self._create_signature(to_digest_xml, '#_0', key_info_data)

        xml = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">'
            f'<s:Header>'
            f'<o:Security xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" s:mustUnderstand="1">'
            f'<u:Timestamp u:Id="_0">'
            f'<u:Created>{created.format_sat()}</u:Created>'
            f'<u:Expires>{expires.format_sat()}</u:Expires>'
            f'</u:Timestamp>'
            f'<o:BinarySecurityToken u:Id="{uuid}" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">'
            f'{certificate}'
            f'</o:BinarySecurityToken>'
            f'{signature_data}'
            f'</o:Security>'
            f'</s:Header>'
            f'<s:Body>'
            f'<Autentica xmlns="http://DescargaMasivaTerceros.gob.mx"/>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        return nospaces(xml)

    def query(self, params: Any) -> str:
        """Route to folio or issued/received query depending on UUID presence."""
        if not params.get_uuid().is_empty():
            return self._query_folio(params)
        return self._query_issued_received(params)

    def verify(self, request_id: str) -> str:
        xml_request_id = self._parse_xml(request_id)
        xml_rfc = self._parse_xml(self._fiel.get_rfc())

        to_digest_xml = (
            f'<des:VerificaSolicitudDescarga xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            f'<des:solicitud IdSolicitud="{xml_request_id}" RfcSolicitante="{xml_rfc}"></des:solicitud>'
            f'</des:VerificaSolicitudDescarga>'
        )
        signature_data = self._create_signature(to_digest_xml)

        xml = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx" xmlns:xd="http://www.w3.org/2000/09/xmldsig#">'
            f'<s:Header/>'
            f'<s:Body>'
            f'<des:VerificaSolicitudDescarga>'
            f'<des:solicitud IdSolicitud="{xml_request_id}" RfcSolicitante="{xml_rfc}">'
            f'{signature_data}'
            f'</des:solicitud>'
            f'</des:VerificaSolicitudDescarga>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        return nospaces(xml)

    def download(self, package_id: str) -> str:
        xml_package_id = self._parse_xml(package_id)
        xml_rfc_owner = self._parse_xml(self._fiel.get_rfc())

        to_digest_xml = (
            f'<des:PeticionDescargaMasivaTercerosEntrada xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            f'<des:peticionDescarga IdPaquete="{xml_package_id}" RfcSolicitante="{xml_rfc_owner}"></des:peticionDescarga>'
            f'</des:PeticionDescargaMasivaTercerosEntrada>'
        )
        signature_data = self._create_signature(to_digest_xml)

        xml = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx" xmlns:xd="http://www.w3.org/2000/09/xmldsig#">'
            f'<s:Header/>'
            f'<s:Body>'
            f'<des:PeticionDescargaMasivaTercerosEntrada>'
            f'<des:peticionDescarga IdPaquete="{xml_package_id}" RfcSolicitante="{xml_rfc_owner}">'
            f'{signature_data}'
            f'</des:peticionDescarga>'
            f'</des:PeticionDescargaMasivaTercerosEntrada>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        return nospaces(xml)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _query_folio(self, params: Any) -> str:
        rfc_signer = self._fiel.get_rfc().upper()
        attributes: Dict[str, str] = {
            'RfcSolicitante': rfc_signer,
            'Folio': params.get_uuid().get_value(),
        }
        return self._build_final_xml('SolicitaDescargaFolio', attributes, '')

    def _query_issued_received(self, params: Any) -> str:
        xml_rfc_received = ''
        request_type = params.get_request_type().get_query_attribute_value(params.get_service_type())
        rfc_signer = self._fiel.get_rfc().upper()
        start = params.get_period().get_start().format('%Y-%m-%dT%H:%M:%S')
        end = params.get_period().get_end().format('%Y-%m-%dT%H:%M:%S')

        if params.get_download_type().is_issued():
            # issued documents, counterparts are receivers
            rfc_issuer = rfc_signer
            rfc_receivers = params.get_rfc_matches()
        else:
            # received documents, counterpart is issuer
            rfc_issuer = params.get_rfc_matches().get_first().get_value()
            rfc_receivers = None  # empty -- will be checked below

        attributes: Dict[str, str] = {
            'RfcSolicitante': rfc_signer,
            'TipoSolicitud': request_type,
            'FechaInicial': start,
            'FechaFinal': end,
            'RfcEmisor': rfc_issuer,
            'TipoComprobante': params.get_document_type().value,
            'EstadoComprobante': params.get_document_status().get_query_attribute_value(),
            'RfcACuentaTerceros': params.get_rfc_on_behalf().get_value(),
            'Complemento': params.get_complement().sat_code(),
        }

        if params.get_download_type().is_received():
            attributes['RfcReceptor'] = rfc_signer

        if rfc_receivers is not None and not rfc_receivers.is_empty():
            receiver_parts = ''.join(
                f'<des:RfcReceptor>{self._parse_xml(rfc_match.get_value())}</des:RfcReceptor>'
                for rfc_match in rfc_receivers
            )
            xml_rfc_received = f'<des:RfcReceptores>{receiver_parts}</des:RfcReceptores>'

        node_name = (
            'SolicitaDescargaEmitidos'
            if params.get_download_type().is_issued()
            else 'SolicitaDescargaRecibidos'
        )

        return self._build_final_xml(node_name, attributes, xml_rfc_received)

    def _build_final_xml(
        self,
        node_name: str,
        attributes: Dict[str, str],
        xml_extra: str,
    ) -> str:
        # Filter out empty-valued attributes
        attributes = {k: v for k, v in attributes.items() if v != ''}
        # Sort by key
        sorted_keys = sorted(attributes.keys())

        solicitud_attrs_text = ' '.join(
            f'{self._parse_xml(name)}="{self._parse_xml(attributes[name])}"'
            for name in sorted_keys
        )

        to_digest_xml = (
            f'<des:{node_name} xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            f'<des:solicitud {solicitud_attrs_text}>'
            f'{xml_extra}'
            f'</des:solicitud>'
            f'</des:{node_name}>'
        )
        signature_data = self._create_signature(to_digest_xml)

        xml = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx" xmlns:xd="http://www.w3.org/2000/09/xmldsig#">'
            f'<s:Header/>'
            f'<s:Body>'
            f'<des:{node_name}>'
            f'<des:solicitud {solicitud_attrs_text}>'
            f'{xml_extra}'
            f'{signature_data}'
            f'</des:solicitud>'
            f'</des:{node_name}>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        return nospaces(xml)

    # ------------------------------------------------------------------
    # XML-DSIG signature creation
    # ------------------------------------------------------------------

    def _create_xml_security_token_id(self) -> str:
        """Generate a UUID-based security token identifier.
        """
        md5 = hashlib.md5(_uuid.uuid4().bytes).hexdigest()  # noqa: S324
        return (
            f'uuid-{md5[0:8]}-{md5[8:12]}-{md5[12:16]}'
            f'-{md5[16:20]}-{md5[20:]}-1'
        )

    def _create_signature(
        self,
        to_digest: str,
        signed_info_uri: str = '',
        key_info: str = '',
    ) -> str:
        """Build a complete ``<Signature>`` element.

        1. ``nospaces(to_digest)`` -> SHA-1 -> base64 = digest value
        2. Build ``<SignedInfo>`` with the digest
        3. Sign the SignedInfo string with RSA-SHA1 -> base64 = signature value
        4. Strip the xmlns from ``<SignedInfo>`` for embedding
        5. Wrap in ``<Signature>`` with ``<SignatureValue>`` and ``<KeyInfo>``
        """
        to_digest = nospaces(to_digest)
        digest_bytes = hashlib.sha1(to_digest.encode('utf-8')).digest()  # noqa: S324
        digested = base64.b64encode(digest_bytes).decode('ascii')

        signed_info = self._create_signed_info_canonical_exclusive(digested, signed_info_uri)

        # Fiel.sign() returns a base64 string
        signature_value = self._fiel.sign(signed_info, 'sha1')

        # Strip the xmlns attribute from <SignedInfo> for embedding inside <Signature>
        signed_info = signed_info.replace(
            '<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">',
            '<SignedInfo>',
        )

        if not key_info:
            key_info = self._create_key_info_data()

        return (
            f'<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
            f'{signed_info}'
            f'<SignatureValue>{signature_value}</SignatureValue>'
            f'{key_info}'
            f'</Signature>'
        )

    def _create_signed_info_canonical_exclusive(self, digested: str, uri: str = '') -> str:
        """Build the ``<SignedInfo>`` element using Exclusive XML Canonicalization 1.0.

        See https://www.w3.org/TR/xmlsec-algorithms/ for algorithm details.
        """
        xml = (
            f'<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">'
            f'<CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"></CanonicalizationMethod>'
            f'<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></SignatureMethod>'
            f'<Reference URI="{uri}">'
            f'<Transforms>'
            f'<Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"></Transform>'
            f'</Transforms>'
            f'<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></DigestMethod>'
            f'<DigestValue>{digested}</DigestValue>'
            f'</Reference>'
            f'</SignedInfo>'
        )
        return nospaces(xml)

    def _create_key_info_data(self) -> str:
        """Build ``<KeyInfo>`` with X509 certificate data."""
        certificate = clean_pem_contents(self._fiel.get_certificate_pem_contents())
        serial = self._fiel.get_certificate_serial()
        issuer_name = self._parse_xml(self._fiel.get_certificate_issuer_name())

        return (
            f'<KeyInfo>'
            f'<X509Data>'
            f'<X509IssuerSerial>'
            f'<X509IssuerName>{issuer_name}</X509IssuerName>'
            f'<X509SerialNumber>{serial}</X509SerialNumber>'
            f'</X509IssuerSerial>'
            f'<X509Certificate>{certificate}</X509Certificate>'
            f'</X509Data>'
            f'</KeyInfo>'
        )

    @staticmethod
    def _parse_xml(text: str) -> str:
        """Escape XML special characters.

        Replaces ``&``, ``<``, ``>``, and ``"`` with their XML entities.
        """
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        return text
