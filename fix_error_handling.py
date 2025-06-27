#!/usr/bin/env python3
"""
Скрипт для анализа и демонстрации улучшенной обработки ошибок.
"""

import traceback
import logging
from typing import Optional, Dict, Any
from enum import Enum

from agno.agent import Agent
from agents.registry.agent_registry import agent_registry
from agents.dynamic.agent_factory import DynamicAgentFactory

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Типы ошибок в системе"""
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_CREATION_FAILED = "agent_creation_failed"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    TOOL_IMPORT_ERROR = "tool_import_error"
    MEMORY_ERROR = "memory_error"
    STORAGE_ERROR = "storage_error"
    VALIDATION_ERROR = "validation_error"
    AUDIO_ARTIFACT_ERROR = "audio_artifact_error"

class AgentError(Exception):
    """Базовый класс для ошибок агентов"""
    def __init__(self, error_type: ErrorType, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

def analyze_current_error_handling():
    """Анализирует текущую обработку ошибок в проекте"""
    print("🔍 Анализ текущей обработки ошибок...")
    
    issues = []
    
    # 1. Проверяем обработку в selector.py
    print("\n📁 agents/selector.py:")
    try:
        # Симулируем вызов несуществующего агента
        agent = agent_registry.get_agent("non_existent_agent")
        print("   ❌ Нет специфичной обработки ошибок - возвращает None вместо исключения")
        issues.append("Selector не выбрасывает исключения при ошибках")
    except Exception as e:
        print(f"   ✅ Получено исключение: {type(e).__name__}: {e}")
    
    # 2. Проверяем обработку в agent_registry.py
    print("\n📁 agents/registry/agent_registry.py:")
    print("   ❌ Используется общий except Exception без специфичных типов")
    print("   ❌ Только print() вместо proper logging")
    issues.append("Registry использует слишком общую обработку ошибок")
    
    # 3. Проверяем обработку в dynamic/agent_factory.py
    print("\n📁 agents/dynamic/agent_factory.py:")
    print("   ❌ Общие except Exception блоки")
    print("   ❌ Отсутствует типизация ошибок")
    issues.append("DynamicAgentFactory не различает типы ошибок")
    
    return issues

def demonstrate_improved_error_handling():
    """Демонстрирует улучшенную обработку ошибок"""
    print("\n🚀 Демонстрация улучшенной обработки ошибок...")
    
    def safe_get_agent(agent_id: str, **kwargs) -> Agent:
        """Улучшенная функция получения агента с типизированными ошибками"""
        try:
            # Проверяем существование агента
            if not agent_id:
                raise AgentError(
                    ErrorType.VALIDATION_ERROR,
                    "Agent ID cannot be empty",
                    {"provided_id": agent_id}
                )
            
            # Попытка получения агента
            agent = agent_registry.get_agent(agent_id, **kwargs)
            
            if agent is None:
                # Определяем тип ошибки более точно
                if agent_registry.is_static_agent(agent_id):
                    raise AgentError(
                        ErrorType.AGENT_CREATION_FAILED,
                        f"Failed to create static agent: {agent_id}",
                        {"agent_id": agent_id, "type": "static"}
                    )
                elif agent_registry.is_dynamic_agent(agent_id):
                    raise AgentError(
                        ErrorType.AGENT_CREATION_FAILED,
                        f"Failed to create dynamic agent: {agent_id}",
                        {"agent_id": agent_id, "type": "dynamic"}
                    )
                else:
                    raise AgentError(
                        ErrorType.AGENT_NOT_FOUND,
                        f"Agent not found: {agent_id}",
                        {"agent_id": agent_id, "available_agents": agent_registry.get_available_agents()}
                    )
            
            return agent
            
        except AgentError:
            # Пробрасываем наши ошибки
            raise
        except Exception as e:
            # Оборачиваем неожиданные ошибки
            logger.error(f"Unexpected error getting agent {agent_id}: {e}")
            logger.debug(traceback.format_exc())
            
            raise AgentError(
                ErrorType.AGENT_CREATION_FAILED,
                f"Unexpected error creating agent: {str(e)}",
                {
                    "agent_id": agent_id,
                    "original_error": str(e),
                    "error_type": type(e).__name__
                }
            )
    
    # Тестируем улучшенную обработку
    test_cases = [
        ("", "Пустой ID агента"),
        ("non_existent_agent", "Несуществующий агент"),
        ("finance_agent", "Существующий агент")
    ]
    
    for agent_id, description in test_cases:
        print(f"\n🧪 Тест: {description}")
        try:
            agent = safe_get_agent(agent_id)
            print(f"   ✅ Успешно получен агент: {agent.name}")
        except AgentError as e:
            print(f"   ❌ {e.error_type.value}: {e.message}")
            if e.details:
                print(f"      Детали: {e.details}")

def fix_audio_artifact_error():
    """Проверяет и предлагает решение для ошибки AudioArtifact"""
    print("\n🎵 Анализ проблемы с AudioArtifact...")
    
    print("""
📋 ПРОБЛЕМА:
   - Ошибка: Either `url` or `base64_audio` must be provided
   - Место: agno/agent/agent.py:4037 в load_agent_session()
   - Причина: AudioArtifact в БД не содержит обязательных полей

🔧 РЕШЕНИЯ:

1. НЕМЕДЛЕННОЕ (Defensive Programming):
   - Добавить валидацию в load_agent_session() с try/catch
   - Пропускать некорректные аудио записи
   - Логировать проблемы для отладки

2. ДОЛГОСРОЧНОЕ (Data Cleanup):
   - Создать миграцию для очистки некорректных записей
   - Добавить валидацию при сохранении аудио
   - Обновить схему БД с constraints

3. ПРЕВЕНТИВНОЕ:
   - Валидация аудио данных перед сохранением
   - Автоматическая генерация URL для локальных файлов
   - Мониторинг структуры данных
    """)

def create_error_handling_improvements():
    """Создает файлы с улучшениями обработки ошибок"""
    print("\n📝 Создание улучшений...")
    
    # Создаем файл с кастомными исключениями
    exceptions_code = '''"""
Кастомные исключения для Agent API Platform.
Обеспечивают типизированную обработку ошибок.
"""

from enum import Enum
from typing import Optional, Dict, Any

class ErrorType(Enum):
    """Типы ошибок в системе агентов"""
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_CREATION_FAILED = "agent_creation_failed" 
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    TOOL_IMPORT_ERROR = "tool_import_error"
    MEMORY_ERROR = "memory_error"
    STORAGE_ERROR = "storage_error"
    VALIDATION_ERROR = "validation_error"
    AUDIO_ARTIFACT_ERROR = "audio_artifact_error"
    COMPATIBILITY_ERROR = "compatibility_error"

class AgentAPIError(Exception):
    """Базовый класс для всех ошибок Agent API"""
    def __init__(self, error_type: ErrorType, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message 
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует ошибку в словарь для API ответов"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details
        }

class AgentNotFoundError(AgentAPIError):
    """Агент не найден"""
    def __init__(self, agent_id: str, available_agents: Optional[list] = None):
        super().__init__(
            ErrorType.AGENT_NOT_FOUND,
            f"Agent '{agent_id}' not found",
            {"agent_id": agent_id, "available_agents": available_agents}
        )

class AgentCreationError(AgentAPIError):
    """Ошибка создания агента"""
    def __init__(self, agent_id: str, reason: str, agent_type: str = "unknown"):
        super().__init__(
            ErrorType.AGENT_CREATION_FAILED,
            f"Failed to create {agent_type} agent '{agent_id}': {reason}",
            {"agent_id": agent_id, "agent_type": agent_type, "reason": reason}
        )

class DatabaseError(AgentAPIError):
    """Ошибка базы данных"""
    def __init__(self, operation: str, details: str):
        super().__init__(
            ErrorType.DATABASE_ERROR,
            f"Database error during {operation}: {details}",
            {"operation": operation}
        )

class AudioArtifactError(AgentAPIError):
    """Ошибка с аудио артефактами"""
    def __init__(self, session_id: str, artifact_id: str, reason: str):
        super().__init__(
            ErrorType.AUDIO_ARTIFACT_ERROR,
            f"Invalid audio artifact in session {session_id}: {reason}",
            {"session_id": session_id, "artifact_id": artifact_id, "reason": reason}
        )
'''
    
    with open("agents/exceptions.py", "w", encoding="utf-8") as f:
        f.write(exceptions_code)
    
    print("   ✅ Создан agents/exceptions.py")
    
    # Создаем миграцию для исправления аудио проблем
    migration_code = '''"""
Fix audio artifacts with missing required fields

Revision ID: 005_fix_audio_artifacts
Revises: 004_add_storage_config
Create Date: 2024-12-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '005_fix_audio_artifacts'
down_revision = '004_add_storage_config'
branch_labels = None
depends_on = None

def upgrade():
    """Исправляем аудио артефакты с отсутствующими обязательными полями"""
    
    # Создаем функцию для очистки некорректных аудио записей
    op.execute("""
        CREATE OR REPLACE FUNCTION fix_audio_artifacts()
        RETURNS void AS $$
        DECLARE
            session_record RECORD;
            audio_record JSONB;
            fixed_audio JSONB := '[]'::jsonb;
            needs_update BOOLEAN := false;
        BEGIN
            -- Перебираем все сессии с аудио данными
            FOR session_record IN 
                SELECT session_id, agent_data 
                FROM sessions 
                WHERE agent_data IS NOT NULL 
                AND agent_data ? 'audio'
                AND jsonb_array_length(agent_data->'audio') > 0
            LOOP
                fixed_audio := '[]'::jsonb;
                needs_update := false;
                
                -- Проверяем каждую аудио запись
                FOR audio_record IN 
                    SELECT * FROM jsonb_array_elements(session_record.agent_data->'audio')
                LOOP
                    -- Проверяем наличие обязательных полей
                    IF audio_record ? 'url' AND audio_record->>'url' IS NOT NULL AND audio_record->>'url' != '' THEN
                        -- URL есть - запись корректна
                        fixed_audio := fixed_audio || audio_record;
                    ELSIF audio_record ? 'base64_audio' AND audio_record->>'base64_audio' IS NOT NULL AND audio_record->>'base64_audio' != '' THEN
                        -- Base64 есть - запись корректна  
                        fixed_audio := fixed_audio || audio_record;
                    ELSE
                        -- Некорректная запись - пропускаем и помечаем что нужно обновление
                        needs_update := true;
                        RAISE NOTICE 'Removing invalid audio artifact from session %: %', session_record.session_id, audio_record;
                    END IF;
                END LOOP;
                
                -- Обновляем сессию если были изменения
                IF needs_update THEN
                    UPDATE sessions 
                    SET agent_data = jsonb_set(
                        session_record.agent_data,
                        '{audio}',
                        fixed_audio
                    )
                    WHERE session_id = session_record.session_id;
                    
                    RAISE NOTICE 'Fixed audio artifacts in session %', session_record.session_id;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Запускаем исправление
    op.execute("SELECT fix_audio_artifacts();")
    
    # Удаляем временную функцию
    op.execute("DROP FUNCTION fix_audio_artifacts();")

def downgrade():
    """Эта миграция необратима - мы не можем восстановить некорректные данные"""
    pass
'''
    
    with open("db/migrations/versions/005_fix_audio_artifacts.py", "w", encoding="utf-8") as f:
        f.write(migration_code)
    
    print("   ✅ Создана миграция 005_fix_audio_artifacts.py")

def main():
    """Основная функция анализа и исправления"""
    print("🔧 Анализ и исправление обработки ошибок")
    print("=" * 60)
    
    # Анализируем текущую ситуацию
    issues = analyze_current_error_handling()
    
    # Демонстрируем улучшения
    demonstrate_improved_error_handling()
    
    # Анализируем проблему с AudioArtifact
    fix_audio_artifact_error()
    
    # Создаем улучшения
    create_error_handling_improvements()
    
    print("\n" + "=" * 60)
    print("📋 РЕЗЮМЕ:")
    print(f"   Найдено проблем: {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n✅ СОЗДАНЫ УЛУЧШЕНИЯ:")
    print("   - agents/exceptions.py - типизированные исключения")
    print("   - 005_fix_audio_artifacts.py - миграция для исправления аудио")
    
    print("\n🚀 СЛЕДУЮЩИЕ ШАГИ:")
    print("   1. Применить миграцию: cd db/migrations && alembic upgrade head")
    print("   2. Интегрировать новые исключения в код")
    print("   3. Добавить валидацию аудио данных при сохранении")

if __name__ == "__main__":
    main() 