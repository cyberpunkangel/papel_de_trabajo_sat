"""
Taxpayer (contribuyente) data routes.
"""

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from app.config.contribuyente_config import ContribuyenteConfig

router = APIRouter()


@router.get("/")
async def load_contribuyente():
    """Load saved taxpayer data."""
    try:
        data = ContribuyenteConfig.load_data()
        return data
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'has_data': False, 'error': str(e)},
        )


@router.post("/")
async def save_contribuyente(
    nombre: str = Form(''),
    rfc: str = Form(''),
    curp: str = Form(''),
):
    """Save taxpayer data."""
    try:
        data = {
            'nombre': nombre,
            'rfc': rfc,
            'curp': curp,
        }

        result = ContribuyenteConfig.save_data(data)

        if result.get('success'):
            return result
        else:
            return JSONResponse(
                status_code=400,
                content=result,
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'message': f'Error del servidor: {e}'},
        )
