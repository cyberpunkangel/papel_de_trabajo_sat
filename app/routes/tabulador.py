"""
ISR tax bracket (tabulador) routes.
"""

from typing import Optional

from fastapi import APIRouter, Form, Query
from fastapi.responses import JSONResponse

from app.config.tabulador_config import TabuladorConfig

router = APIRouter()


@router.get("/")
async def load_tabulador(period: Optional[str] = Query(None)):
    """Load tabulador data for a given period."""
    try:
        data = TabuladorConfig.load_data(period)
        return {
            'has_data': data.get('has_data', False),
            'period': data.get('period'),
            'rows': data.get('rows', []),
            'updated_at': data.get('updated_at'),
            'available_periods': data.get('available_periods', []),
        }
    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={
                'has_data': False,
                'rows': [],
                'message': str(e),
            },
        )


@router.post("/")
async def save_tabulador(
    periodo: str = Form(''),
    tabulador_isr: str = Form(''),
    tabulador_periodo: str = Form(''),
):
    """Save tabulador ISR data."""
    try:
        # Use periodo or tabulador_periodo
        period = periodo or tabulador_periodo
        result = TabuladorConfig.save_from_payload(period, tabulador_isr)

        return {
            'success': True,
            'message': 'Tabulador ISR guardado correctamente.',
            'period': result.get('period'),
            'rows': result.get('rows'),
            'updated_at': result.get('updated_at'),
            'available_periods': result.get('available_periods', []),
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': str(e)},
        )
    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'message': str(e)},
        )
