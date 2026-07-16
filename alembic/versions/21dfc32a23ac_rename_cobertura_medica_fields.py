"""rename_cobertura_medica_fields

Revision ID: 21dfc32a23ac
Revises: 441cec87cd4a
Create Date: 2026-07-16 10:48:57.313978
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21dfc32a23ac'
down_revision: Union[str, None] = '441cec87cd4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('coberturas_medicas', 'id_obra_social', new_column_name='entidadFinanciadoraId')
    op.alter_column('coberturas_medicas', 'codigo_plan', new_column_name='planId')
    op.add_column('coberturas_medicas', sa.Column('nombre_plan', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('coberturas_medicas', 'nombre_plan')
    op.alter_column('coberturas_medicas', 'planId', new_column_name='codigo_plan')
    op.alter_column('coberturas_medicas', 'entidadFinanciadoraId', new_column_name='id_obra_social')

