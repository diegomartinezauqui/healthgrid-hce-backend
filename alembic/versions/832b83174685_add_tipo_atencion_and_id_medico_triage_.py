"""add_tipo_atencion_and_id_medico_triage_to_sala_espera

Revision ID: 832b83174685
Revises: e4ba5d50f533
Create Date: 2026-06-22 18:59:27.052871
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '832b83174685'
down_revision: Union[str, None] = 'e4ba5d50f533'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear enum en Postgres si no existe
    tipo_atencion_enum = sa.Enum('consultorio', 'guardia', 'cirugia', 'demanda_espontanea', name='tipo_atencion_enum')
    tipo_atencion_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('sala_espera', sa.Column('tipo_atencion', sa.Enum('consultorio', 'guardia', 'cirugia', 'demanda_espontanea', name='tipo_atencion_enum'), nullable=False, server_default='consultorio'))
    op.add_column('sala_espera', sa.Column('id_medico_triage', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('sala_espera', 'id_medico_triage')
    op.drop_column('sala_espera', 'tipo_atencion')
    op.execute('DROP TYPE tipo_atencion_enum')
