"""add_finalizado_to_estado_sala_espera

Revision ID: e4ba5d50f533
Revises: 1f275ca4e1c9
Create Date: 2026-06-22 13:14:09.408920
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4ba5d50f533'
down_revision: Union[str, None] = '1f275ca4e1c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos el nuevo valor al tipo ENUM en PostgreSQL.
    op.execute("ALTER TYPE estado_sala_espera ADD VALUE 'Finalizado'")


def downgrade() -> None:
    # PostgreSQL no permite remover valores de ENUM de forma simple.
    pass
