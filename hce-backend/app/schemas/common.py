"""Schemas comunes: ErrorResponse, HealthResponse, etc."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Respuesta estándar de error del módulo HCE."""

    error: str = Field(..., examples=["NOT_FOUND"])
    message: str = Field(..., examples=["El recurso solicitado no fue encontrado."])
    timestamp: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Respuesta del health check."""

    status: str = Field(..., examples=["UP"])
    module: str = Field(..., examples=["hce"])
    timestamp: datetime


class SuccessResponse(BaseModel):
    """Respuesta genérica de éxito."""

    status: str = Field(default="success", examples=["success"])
    message: str = Field(..., examples=["Operación realizada correctamente."])
