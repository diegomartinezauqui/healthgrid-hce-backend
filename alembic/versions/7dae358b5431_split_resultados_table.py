"""split_resultados_table

Revision ID: 7dae358b5431
Revises: efc70817c09e
Create Date: 2026-06-25 18:05:00.123456
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7dae358b5431'
down_revision: Union[str, None] = 'efc70817c09e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old table resultados_estudios
    op.drop_table('resultados_estudios')

    # 2. Create resultados_laboratorio table
    op.create_table(
        'resultados_laboratorio',
        sa.Column('id_resultado_laboratorio', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_orden', sa.Integer(), nullable=True),
        sa.Column('id_paciente', sa.Integer(), nullable=False),
        sa.Column('id_profesional_firmante', sa.String(length=200), nullable=False),
        sa.Column('fecha_resultado', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('informe_resumen', sa.Text(), nullable=True),
        sa.Column('id_externo_estudio', sa.String(length=100), nullable=True),
        sa.Column('analitos', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
        sa.Column('resumen_analitos', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
        sa.ForeignKeyConstraint(['id_orden'], ['ordenes.id_orden'], ),
        sa.ForeignKeyConstraint(['id_paciente'], ['pacientes.id_paciente'], ),
        sa.PrimaryKeyConstraint('id_resultado_laboratorio')
    )
    op.create_index(op.f('ix_resultados_laboratorio_id_paciente'), 'resultados_laboratorio', ['id_paciente'], unique=False)

    # 3. Create resultados_imagenes table
    subtipo_enum = postgresql.ENUM('ECOGRAFY', 'RADIOLOGY', 'TOMOGRAPHY', 'RESONANCE', 'MAMMOGRAPHY', 'DENSITOMETRY', 'ECODOPPLER', 'ENDOSCOPY', name='subtipo_estudio_enum', create_type=False)
    op.create_table(
        'resultados_imagenes',
        sa.Column('id_resultado_imagen', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_orden', sa.Integer(), nullable=True),
        sa.Column('id_paciente', sa.Integer(), nullable=False),
        sa.Column('id_profesional_firmante', sa.String(length=200), nullable=False),
        sa.Column('fecha_resultado', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('titulo', sa.String(length=300), nullable=True),
        sa.Column('informe_resumen', sa.Text(), nullable=True),
        sa.Column('id_externo_estudio', sa.String(length=100), nullable=True),
        sa.Column('subtipo', subtipo_enum, nullable=True),
        sa.Column('link_imagen', sa.String(length=500), nullable=True),
        sa.Column('url_detalle', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['id_orden'], ['ordenes.id_orden'], ),
        sa.ForeignKeyConstraint(['id_paciente'], ['pacientes.id_paciente'], ),
        sa.PrimaryKeyConstraint('id_resultado_imagen')
    )
    op.create_index(op.f('ix_resultados_imagenes_id_paciente'), 'resultados_imagenes', ['id_paciente'], unique=False)


def downgrade() -> None:
    # 1. Drop new tables
    op.drop_index(op.f('ix_resultados_imagenes_id_paciente'), table_name='resultados_imagenes')
    op.drop_table('resultados_imagenes')
    op.drop_index(op.f('ix_resultados_laboratorio_id_paciente'), table_name='resultados_laboratorio')
    op.drop_table('resultados_laboratorio')

    # 2. Recreate old table resultados_estudios
    tipo_estudio_enum = postgresql.ENUM('Laboratorio', 'Imagen', 'Anatomia_Patologica', name='tipo_estudio_resultado', create_type=False)
    subtipo_enum = postgresql.ENUM('ECOGRAFY', 'RADIOLOGY', 'TOMOGRAPHY', 'RESONANCE', 'MAMMOGRAPHY', 'DENSITOMETRY', 'ECODOPPLER', 'ENDOSCOPY', name='subtipo_estudio_enum', create_type=False)
    op.create_table(
        'resultados_estudios',
        sa.Column('id_resultado', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_orden', sa.Integer(), nullable=True),
        sa.Column('id_paciente', sa.Integer(), nullable=False),
        sa.Column('tipo_estudio', tipo_estudio_enum, nullable=False),
        sa.Column('id_profesional_firmante', sa.String(length=200), nullable=False),
        sa.Column('fecha_resultado', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('informe_resumen', sa.Text(), nullable=True),
        sa.Column('id_externo_estudio', sa.String(length=100), nullable=True),
        sa.Column('titulo', sa.String(length=300), nullable=True),
        sa.Column('resumen', sa.Text(), nullable=True),
        sa.Column('subtipo', subtipo_enum, nullable=True),
        sa.Column('link_imagen', sa.String(length=500), nullable=True),
        sa.Column('url_detalle', sa.String(length=500), nullable=True),
        sa.Column('analitos', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
        sa.Column('resumen_analitos', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
        sa.ForeignKeyConstraint(['id_orden'], ['ordenes.id_orden'], ),
        sa.ForeignKeyConstraint(['id_paciente'], ['pacientes.id_paciente'], ),
        sa.PrimaryKeyConstraint('id_resultado')
    )
    op.create_index('ix_resultados_estudios_id_paciente', 'resultados_estudios', ['id_paciente'], unique=False)
