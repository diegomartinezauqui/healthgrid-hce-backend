"""add_details_to_ordenes

Revision ID: efc70817c09e
Revises: d77dfb3fa6ee
Create Date: 2026-06-25 17:35:10.123456
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'efc70817c09e'
down_revision: Union[str, None] = 'd77dfb3fa6ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    subtipo_enum = sa.Enum('ECOGRAFY', 'RADIOLOGY', 'TOMOGRAPHY', 'RESONANCE', 'MAMMOGRAPHY', 'DENSITOMETRY', 'ECODOPPLER', 'ENDOSCOPY', name='subtipo_estudio_enum')
    op.add_column('ordenes', sa.Column('subtipo', subtipo_enum, nullable=True))
    op.add_column('ordenes', sa.Column('estudio_ids', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True))


def downgrade() -> None:
    op.drop_column('ordenes', 'estudio_ids')
    op.drop_column('ordenes', 'subtipo')
