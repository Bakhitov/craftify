"""add cache triggers

Revision ID: 003_add_cache_triggers
Revises: 13622ee893de_add_storage_config_to_dynamic_agents
Create Date: 2024-12-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_cache_triggers'
down_revision: Union[str, None] = '002_update_agent_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет триггеры PostgreSQL NOTIFY для автоматического обновления кэша"""
    
    # Создаем функцию для уведомления об изменениях агентов
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_agent_change()
        RETURNS trigger AS $$
        BEGIN
            -- Отправляем уведомление с деталями изменения
            PERFORM pg_notify('agent_changes', json_build_object(
                'agent_id', COALESCE(NEW.agent_id, OLD.agent_id),
                'action', TG_OP,
                'table', TG_TABLE_NAME,
                'timestamp', extract(epoch from now())
            )::text);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Создаем функцию для уведомления об изменениях инструментов
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_tool_change()
        RETURNS trigger AS $$
        BEGIN
            -- Отправляем уведомление с деталями изменения
            PERFORM pg_notify('tool_changes', json_build_object(
                'tool_id', COALESCE(NEW.tool_id, OLD.tool_id),
                'action', TG_OP,
                'table', TG_TABLE_NAME,
                'timestamp', extract(epoch from now())
            )::text);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Добавляем триггеры для таблицы динамических агентов
    op.execute("""
        CREATE TRIGGER agent_change_trigger
            AFTER INSERT OR UPDATE OR DELETE ON dynamic_agents
            FOR EACH ROW EXECUTE FUNCTION notify_agent_change();
    """)
    
    # Добавляем триггеры для таблицы динамических инструментов
    op.execute("""
        CREATE TRIGGER tool_change_trigger
            AFTER INSERT OR UPDATE OR DELETE ON dynamic_tools
            FOR EACH ROW EXECUTE FUNCTION notify_tool_change();
    """)
    
    # Создаем функцию для ручного уведомления (для использования в API)
    op.execute("""
        CREATE OR REPLACE FUNCTION manual_cache_notify(
            channel_name TEXT,
            payload JSON
        )
        RETURNS void AS $$
        BEGIN
            PERFORM pg_notify(channel_name, payload::text);
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Удаляет триггеры и функции"""
    
    # Удаляем триггеры
    op.execute("DROP TRIGGER IF EXISTS agent_change_trigger ON dynamic_agents;")
    op.execute("DROP TRIGGER IF EXISTS tool_change_trigger ON dynamic_tools;")
    
    # Удаляем функции
    op.execute("DROP FUNCTION IF EXISTS notify_agent_change();")
    op.execute("DROP FUNCTION IF EXISTS notify_tool_change();")
    op.execute("DROP FUNCTION IF EXISTS manual_cache_notify(TEXT, JSON);") 