"""Create dynamic entities tables

Revision ID: 001_create_dynamic_entities
Revises: 
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_create_dynamic_entities'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Используем схему public (по умолчанию)
    
    # Таблица для динамических агентов
    op.create_table('dynamic_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('model_config', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('tools_config', postgresql.JSONB(), nullable=True, default='[]'),
        sa.Column('knowledge_config', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('memory_config', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('settings', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id')
    )
    
    # Таблица для динамических инструментов
    op.create_table('dynamic_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tool_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('function_name', sa.String(255), nullable=False),
        sa.Column('parameters_schema', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('implementation', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tool_id')
    )
    
    # Таблица для динамических команд
    op.create_table('dynamic_teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('team_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('mode', sa.String(50), nullable=True, default='coordinate'),
        sa.Column('members_config', postgresql.JSONB(), nullable=True, default='[]'),
        sa.Column('settings', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id')
    )
    
    # Таблица для динамических workflow
    op.create_table('dynamic_workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('workflow_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('steps_config', postgresql.JSONB(), nullable=True, default='[]'),
        sa.Column('settings', postgresql.JSONB(), nullable=True, default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_id')
    )
    
    # Создаем индексы для быстрого поиска
    op.create_index('idx_dynamic_agents_active', 'dynamic_agents', ['is_active'])
    op.create_index('idx_dynamic_tools_active', 'dynamic_tools', ['is_active'])
    op.create_index('idx_dynamic_teams_active', 'dynamic_teams', ['is_active'])
    op.create_index('idx_dynamic_workflows_active', 'dynamic_workflows', ['is_active'])


def downgrade():
    # Удаляем индексы
    op.drop_index('idx_dynamic_workflows_active', 'dynamic_workflows')
    op.drop_index('idx_dynamic_teams_active', 'dynamic_teams')
    op.drop_index('idx_dynamic_tools_active', 'dynamic_tools')
    op.drop_index('idx_dynamic_agents_active', 'dynamic_agents')
    
    # Удаляем таблицы
    op.drop_table('dynamic_workflows')
    op.drop_table('dynamic_teams')
    op.drop_table('dynamic_tools')
    op.drop_table('dynamic_agents') 