"""add_storage_config_to_dynamic_agents

Revision ID: 13622ee893de
Revises: 001_create_dynamic_entities
Create Date: 2024-12-19 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '13622ee893de'
down_revision: Union[str, None] = '001_create_dynamic_entities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку storage_config в таблицу dynamic_agents
    op.add_column('dynamic_agents', 
                  sa.Column('storage_config', postgresql.JSONB(), nullable=True, default='{}'))


def downgrade() -> None:
    # Удаляем колонку storage_config из таблицы dynamic_agents
    op.drop_column('dynamic_agents', 'storage_config')
