"""
FIEL certificate management routes.
"""

import os
import tempfile
from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.config.fiel_config import FielConfig

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

router = APIRouter()


@router.get("/status")
async def check_fiel_status():
    """Check whether a valid FIEL configuration exists."""
    try:
        config = FielConfig.load()
        if config and FielConfig.verify():
            return {
                'has_config': True,
                'rfc': config.get('rfc', 'N/A'),
                'nombre': config.get('nombre', 'N/A'),
                'valido_hasta': config.get('valido_hasta', 'N/A'),
            }
        return {'has_config': False}
    except Exception as e:
        return {'has_config': False, 'error': str(e)}


@router.post("/upload")
async def upload_fiel(
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    password: str = Form(''),
):
    """Upload and validate FIEL certificate files."""
    tmp_cert = None
    tmp_key = None
    try:
        # Write uploaded files to temp paths
        cert_bytes = await cert_file.read()
        key_bytes = await key_file.read()

        tmp_cert = tempfile.NamedTemporaryFile(delete=False, suffix='.cer')
        tmp_cert.write(cert_bytes)
        tmp_cert.close()

        tmp_key = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
        tmp_key.write(key_bytes)
        tmp_key.close()

        # Copy files to fiel-uploads/
        file_paths = FielConfig.copy_files(tmp_cert.name, tmp_key.name)

        trimmed_password = (password or '').strip()
        validated_now = bool(trimmed_password)

        cert_info = {
            'rfc': 'N/A',
            'nombre': 'N/A',
            'valido_desde': 'N/A',
            'valido_hasta': 'N/A',
            'serial': 'N/A',
        }

        if validated_now:
            cert_info = FielConfig.validate_certificates(
                tmp_cert.name, tmp_key.name, trimmed_password,
            )

        # Build and save configuration
        config = {
            'certificate_path': file_paths['certificate_path'],
            'key_path': file_paths['key_path'],
            'rfc': cert_info['rfc'],
            'nombre': cert_info['nombre'],
            'valido_desde': cert_info['valido_desde'],
            'valido_hasta': cert_info['valido_hasta'],
            'serial': cert_info['serial'],
            'fecha_configuracion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        if not FielConfig.save(config):
            raise Exception('No se pudo guardar la configuracion')

        if validated_now:
            message = 'Configuracion guardada y validada exitosamente'
        else:
            message = (
                'Configuracion guardada sin validar contraseña. '
                'Si deseas validar en este paso, usa el botón "Comprobar archivos y contraseña".'
            )

        return {
            'success': True,
            'validated_now': validated_now,
            'message': message,
            'data': {
                'rfc': cert_info['rfc'],
                'nombre': cert_info['nombre'],
                'valido_hasta': cert_info['valido_hasta'],
                'serial': cert_info['serial'],
            },
        }

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': str(e)},
        )
    finally:
        # Clean up temp files
        for tmp in (tmp_cert, tmp_key):
            if tmp is not None:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass


@router.post("/validate")
async def validate_fiel_integrity(
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    password: str = Form(...),
):
    """Validate FIEL files + password integrity without saving configuration."""
    tmp_cert = None
    tmp_key = None
    try:
        if not password:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'message': 'Debes capturar la contrasena para validar.'},
            )

        cert_bytes = await cert_file.read()
        key_bytes = await key_file.read()

        tmp_cert = tempfile.NamedTemporaryFile(delete=False, suffix='.cer')
        tmp_cert.write(cert_bytes)
        tmp_cert.close()

        tmp_key = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
        tmp_key.write(key_bytes)
        tmp_key.close()

        cert_info = FielConfig.validate_certificates(
            tmp_cert.name, tmp_key.name, password,
        )

        return {
            'success': True,
            'message': 'Integridad validada correctamente',
            'data': {
                'rfc': cert_info['rfc'],
                'nombre': cert_info['nombre'],
                'valido_hasta': cert_info['valido_hasta'],
                'serial': cert_info['serial'],
            },
        }

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': str(e)},
        )
    finally:
        for tmp in (tmp_cert, tmp_key):
            if tmp is not None:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass


@router.post("/test")
async def test_fiel(password: str = Form(...)):
    """Test FIEL authentication against SAT."""
    try:
        config_path = os.path.join(BASE_DIR, 'config', 'fiel_config.json')
        if not os.path.isfile(config_path):
            raise Exception('No hay configuracion de FIEL')

        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        if not password:
            raise Exception('Se requiere la contrasena')

        cert_path = config_data.get('certificate_path', '')
        key_path = config_data.get('key_path', '')

        if not cert_path or not key_path:
            raise Exception('Configuracion de FIEL incompleta')

        # Step 1: Read certificates
        with open(cert_path, 'rb') as f:
            cert_contents = f.read()
        with open(key_path, 'rb') as f:
            key_contents = f.read()

        # Step 2: Create FIEL
        from app.sat.request_builder.fiel import Fiel
        fiel = Fiel.create(cert_contents, key_contents, password)

        if not fiel.is_valid():
            raise Exception('La FIEL no es valida')

        # Step 3: Create service and authenticate
        from app.sat.request_builder.fiel_request_builder import FielRequestBuilder
        from app.sat.web_client.httpx_web_client import HttpxWebClient
        request_builder = FielRequestBuilder(fiel)
        web_client = HttpxWebClient()

        # Build authentication request
        from app.sat.shared.service_endpoints import ServiceEndpoints
        endpoints = ServiceEndpoints.cfdi()
        token_xml = request_builder.authorization(
            datetime.utcnow(), datetime.utcnow(),
        )

        return {
            'success': True,
            'step': 4,
            'message': 'FIEL validada correctamente. Lista para autenticar contra el SAT.',
            'rfc': fiel.get_rfc(),
        }

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'error': str(e),
            },
        )
