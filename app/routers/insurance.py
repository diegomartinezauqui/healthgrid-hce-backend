"""
Endpoint de cobertura médica — Integración M7 (Facturación).
HCE expone → Facturación consume para aplicar nomenclador.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.models.cobertura_medica import CoberturaMedica
from app.schemas.common import ErrorResponse
from app.schemas.insurance import InsuranceResponse

router = APIRouter()


@router.get(
    "/patients/{id_paciente}/insurance",
    response_model=InsuranceResponse,
    summary="Obtener cobertura médica vigente del paciente",
    description=(
        "Retorna la obra social o prepaga vigente del paciente. "
        "Facturación necesita este dato para aplicar el nomenclador correcto."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_cobertura(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:insurance:read")),
):
    result = await db.execute(
        select(CoberturaMedica)
        .where(CoberturaMedica.id_paciente == id_paciente)
        .order_by(CoberturaMedica.vigente_desde.desc())
        .limit(1)
    )
    cobertura = result.scalar_one_or_none()

    if not cobertura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )

    return InsuranceResponse.model_validate(cobertura)
