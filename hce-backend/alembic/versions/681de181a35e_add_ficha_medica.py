"""add_ficha_medica

Revision ID: 681de181a35e
Revises: 84d45f6d7169
Create Date: 2026-05-15 19:56:07.667324
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
"""add_ficha_medica

Revision ID: 681de181a35e
Revises: 84d45f6d7169
Create Date: 2026-05-15 19:56:07.667324
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '681de181a35e'
down_revision: Union[str, None] = '84d45f6d7169'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('fichas_medicas',
    sa.Column('id_paciente', sa.Integer(), nullable=False),
    sa.Column('grupo_sanguineo', sa.String(length=10), nullable=True),
    sa.Column('peso_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('altura_cm', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('observaciones_generales', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['id_paciente'], ['pacientes.id_paciente'], ),
    sa.PrimaryKeyConstraint('id_paciente')
    )


def downgrade() -> None:
    op.drop_table('fichas_medicas')
