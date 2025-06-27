"""Add storage_config to dynamic_agents

Revision ID: 004_add_storage_config
Revises: 003_add_cache_triggers
Create Date: 2024-12-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004_add_storage_config'
down_revision = '003_add_cache_triggers'
branch_labels = None
depends_on = None

def upgrade():
    """Добавляем поле storage_config если его нет"""
    # Проверяем существует ли уже столбец
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    columns = [col['name'] for col in inspector.get_columns('dynamic_agents')]
    
    if 'storage_config' not in columns:
        op.add_column('dynamic_agents', 
            sa.Column('storage_config', postgresql.JSONB(), nullable=True, default='{}')
        )
        print("✅ Добавлено поле storage_config в таблицу dynamic_agents")
    else:
        print("ℹ️ Поле storage_config уже существует в таблице dynamic_agents")

def downgrade():
    """Удаляем поле storage_config"""
    op.drop_column('dynamic_agents', 'storage_config') 