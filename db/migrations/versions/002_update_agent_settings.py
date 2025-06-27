"""Update agent settings with missing agno built-in tools parameters

Revision ID: 002_update_agent_settings
Revises: 001_create_dynamic_entities
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '002_update_agent_settings'
down_revision: Union[str, None] = '001_create_dynamic_entities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновляет настройки существующих агентов, добавляя недостающие параметры для встроенных инструментов agno"""
    
    # Подключаемся к базе данных
    connection = op.get_bind()
    
    # Получаем всех агентов
    result = connection.execute(text("""
        SELECT id, settings 
        FROM dynamic_agents 
        WHERE settings IS NOT NULL
    """))
    
    # Дефолтные настройки для встроенных инструментов agno
    default_settings_update = {
        # Параметры для активации встроенных инструментов agno
        "read_chat_history": False,
        "search_knowledge": True,
        "update_knowledge": False,
        "read_tool_call_history": False,
        "search_previous_sessions_history": False,
        "num_history_sessions": None,
        
        # Дополнительные настройки agno
        "enable_user_memories": False,
        "add_memory_references": None,
        "enable_session_summaries": False,
        "add_session_summary_references": None,
        
        # Настройки knowledge
        "add_references": False,
        "enable_agentic_knowledge_filters": False,
        
        # Настройки reasoning
        "reasoning": False,
        "reasoning_min_steps": 1,
        "reasoning_max_steps": 10,
    }
    
    # Обновляем каждого агента
    for row in result:
        agent_id = row[0]
        current_settings = row[1] or {}
        
        # Добавляем недостающие параметры
        updated_settings = {**current_settings}
        for key, value in default_settings_update.items():
            if key not in updated_settings:
                updated_settings[key] = value
        
        # Обновляем запись в БД
        connection.execute(text("""
            UPDATE dynamic_agents 
            SET settings = :settings, updated_at = CURRENT_TIMESTAMP
            WHERE id = :agent_id
        """), {
            "settings": sa.dialects.postgresql.json.dumps(updated_settings),
            "agent_id": agent_id
        })
    
    # Также обновляем агентов с пустыми settings
    connection.execute(text("""
        UPDATE dynamic_agents 
        SET settings = :default_settings, updated_at = CURRENT_TIMESTAMP
        WHERE settings IS NULL
    """), {
        "default_settings": sa.dialects.postgresql.json.dumps(default_settings_update)
    })


def downgrade() -> None:
    """Откатывает изменения, удаляя добавленные параметры из settings"""
    
    connection = op.get_bind()
    
    # Список параметров для удаления
    params_to_remove = [
        "read_chat_history",
        "search_knowledge", 
        "update_knowledge",
        "read_tool_call_history",
        "search_previous_sessions_history",
        "num_history_sessions",
        "enable_user_memories",
        "add_memory_references",
        "enable_session_summaries",
        "add_session_summary_references",
        "add_references",
        "enable_agentic_knowledge_filters",
        "reasoning",
        "reasoning_min_steps",
        "reasoning_max_steps",
    ]
    
    # Получаем всех агентов
    result = connection.execute(text("""
        SELECT id, settings 
        FROM dynamic_agents 
        WHERE settings IS NOT NULL
    """))
    
    # Удаляем добавленные параметры
    for row in result:
        agent_id = row[0]
        current_settings = row[1] or {}
        
        # Удаляем параметры
        updated_settings = {k: v for k, v in current_settings.items() if k not in params_to_remove}
        
        # Обновляем запись в БД
        connection.execute(text("""
            UPDATE dynamic_agents 
            SET settings = :settings, updated_at = CURRENT_TIMESTAMP
            WHERE id = :agent_id
        """), {
            "settings": sa.dialects.postgresql.json.dumps(updated_settings) if updated_settings else None,
            "agent_id": agent_id
        }) 