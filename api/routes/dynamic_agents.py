"""
API маршруты для управления динамическими агентами.
Обеспечивает CRUD операции для динамических агентов в БД.
"""
import json
from logging import getLogger
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from db.session import SessionLocal
from agents.selector import refresh_agent_cache, get_agent_info

# Импортируем типизированные модели
from agents.models import (
    DynamicAgentConfig,
    ModelConfig,
    StaticToolConfig,
    DynamicToolConfig,
    KnowledgeConfig,
    MemoryConfig,
    StorageConfig,
    AgentSettings
)

logger = getLogger(__name__)

######################################################
## Routes for Dynamic Agents Management
######################################################

dynamic_agents_router = APIRouter(prefix="/dynamic-agents", tags=["Dynamic Agents"])


class DynamicAgentRequest(BaseModel):
    """Модель запроса для создания/обновления динамического агента"""
    model_config = {"populate_by_name": True}
    
    name: str = Field(..., description="Имя агента")
    agent_id: str = Field(..., description="Уникальный ID агента")
    description: Optional[str] = Field(None, description="Описание агента")
    instructions: Optional[str] = Field(None, description="Инструкции для агента")
    
    # Используем типизированные модели вместо Dict[str, Any]
    model_config_data: ModelConfig = Field(default_factory=ModelConfig, description="Конфигурация модели", alias="model_config")
    tools_config: List[Dict[str, Any]] = Field(default_factory=list, description="Конфигурация инструментов")  # Пока оставляем Dict для совместимости
    knowledge_config: KnowledgeConfig = Field(default_factory=KnowledgeConfig, description="Конфигурация знаний")
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig, description="Конфигурация памяти")
    storage_config: StorageConfig = Field(default_factory=StorageConfig, description="Конфигурация хранилища")
    settings: AgentSettings = Field(default_factory=AgentSettings, description="Настройки агента")


class DynamicAgentResponse(BaseModel):
    """Модель ответа с информацией о динамическом агенте"""
    model_config = {"populate_by_name": True}
    
    id: int
    name: str
    agent_id: str
    description: Optional[str]
    instructions: Optional[str]
    
    # Используем типизированные модели
    model_config_data: ModelConfig = Field(alias="model_config")
    tools_config: List[Dict[str, Any]]  # Пока оставляем Dict для совместимости
    knowledge_config: KnowledgeConfig
    memory_config: MemoryConfig
    storage_config: StorageConfig
    settings: AgentSettings
    
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dynamic_agents_router.get("", response_model=List[DynamicAgentResponse])
async def list_dynamic_agents():
    """
    Возвращает список всех динамических агентов.
    
    Returns:
        List[DynamicAgentResponse]: Список динамических агентов
    """
    with SessionLocal() as session:
        try:
            query = text("""
                SELECT id, name, agent_id, description, instructions,
                       model_config, tools_config, knowledge_config,
                       memory_config, storage_config, settings, is_active, 
                       created_at, updated_at
                FROM dynamic_agents
                ORDER BY created_at DESC
            """)
            
            result = session.execute(query)
            agents = []
            
            for row in result.fetchall():
                agents.append(DynamicAgentResponse(
                    id=row.id,
                    name=row.name,
                    agent_id=row.agent_id,
                    description=row.description,
                    instructions=row.instructions,
                    model_config_data=ModelConfig(**(json.loads(row.model_config) if row.model_config else {})),
                    tools_config=json.loads(row.tools_config) if row.tools_config else [],
                    knowledge_config=KnowledgeConfig(**(json.loads(row.knowledge_config) if row.knowledge_config else {})),
                    memory_config=MemoryConfig(**(json.loads(row.memory_config) if row.memory_config else {})),
                    storage_config=StorageConfig(**(json.loads(row.storage_config) if row.storage_config else {})),
                    settings=AgentSettings(**(json.loads(row.settings) if row.settings else {})),
                    is_active=row.is_active,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                ))
            
            return agents
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка динамических агентов: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить список динамических агентов"
            )


@dynamic_agents_router.get("/{agent_id}", response_model=DynamicAgentResponse)
async def get_dynamic_agent(agent_id: str):
    """
    Возвращает информацию о конкретном динамическом агенте.
    
    Args:
        agent_id: ID агента
        
    Returns:
        DynamicAgentResponse: Информация об агенте
    """
    with SessionLocal() as session:
        try:
            query = text("""
                SELECT id, name, agent_id, description, instructions,
                       model_config, tools_config, knowledge_config,
                       memory_config, storage_config, settings, is_active,
                       created_at, updated_at
                FROM dynamic_agents
                WHERE agent_id = :agent_id
            """)
            
            result = session.execute(query, {"agent_id": agent_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Динамический агент {agent_id} не найден"
                )
            
            response = DynamicAgentResponse(
                id=row.id,
                name=row.name,
                agent_id=row.agent_id,
                description=row.description,
                instructions=row.instructions,
                model_config_data=ModelConfig(**(json.loads(row.model_config) if row.model_config else {})),
                tools_config=json.loads(row.tools_config) if row.tools_config else [],
                knowledge_config=KnowledgeConfig(**(json.loads(row.knowledge_config) if row.knowledge_config else {})),
                memory_config=MemoryConfig(**(json.loads(row.memory_config) if row.memory_config else {})),
                storage_config=StorageConfig(**(json.loads(row.storage_config) if row.storage_config else {})),
                settings=AgentSettings(**(json.loads(row.settings) if row.settings else {})),
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка при получении динамического агента {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось получить динамического агента {agent_id}"
            )


@dynamic_agents_router.post("", response_model=DynamicAgentResponse, status_code=status.HTTP_201_CREATED)
async def create_dynamic_agent(agent_data: DynamicAgentRequest):
    """
    Создает нового динамического агента.
    
    Args:
        agent_data: Данные для создания агента
        
    Returns:
        DynamicAgentResponse: Созданный агент
    """
    with SessionLocal() as session:
        try:
            # Проверяем уникальность agent_id
            check_query = text("""
                SELECT COUNT(*) as count FROM dynamic_agents 
                WHERE agent_id = :agent_id
            """)
            
            result = session.execute(check_query, {"agent_id": agent_data.agent_id})
            if result.fetchone().count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Агент с ID {agent_data.agent_id} уже существует"
                )
            
            # Создаем нового агента
            result = session.execute(text("""
                INSERT INTO dynamic_agents 
                (name, agent_id, description, instructions, model_config, 
                 tools_config, knowledge_config, memory_config, storage_config, settings)
                VALUES (%(name)s, %(agent_id)s, %(description)s, %(instructions)s, 
                        %(model_config)s, %(tools_config)s, %(knowledge_config)s, 
                        %(memory_config)s, %(storage_config)s, %(settings)s)
                RETURNING id, created_at, updated_at
            """), {
                "name": agent_data.name,
                "agent_id": agent_data.agent_id,
                "description": agent_data.description,
                "instructions": agent_data.instructions,
                "model_config": json.dumps(agent_data.model_config_data.model_dump()),
                "tools_config": json.dumps(agent_data.tools_config),
                "knowledge_config": json.dumps(agent_data.knowledge_config.model_dump()),
                "memory_config": json.dumps(agent_data.memory_config.model_dump()),
                "storage_config": json.dumps(agent_data.storage_config.model_dump()),
                "settings": json.dumps(agent_data.settings.model_dump())
            })
            
            row = result.fetchone()
            session.commit()
            
            # Обновляем кэш
            refresh_agent_cache()
            
            return DynamicAgentResponse(
                id=row.id,
                name=agent_data.name,
                agent_id=agent_data.agent_id,
                description=agent_data.description,
                instructions=agent_data.instructions,
                model_config_data=agent_data.model_config_data,
                tools_config=agent_data.tools_config,
                knowledge_config=agent_data.knowledge_config,
                memory_config=agent_data.memory_config,
                storage_config=agent_data.storage_config,
                settings=agent_data.settings,
                is_active=True,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при создании динамического агента: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать динамического агента"
            )


@dynamic_agents_router.put("/{agent_id}", response_model=DynamicAgentResponse)
async def update_dynamic_agent(agent_id: str, agent_data: DynamicAgentRequest):
    """
    Обновляет существующего динамического агента.
    
    Args:
        agent_id: ID агента для обновления
        agent_data: Новые данные агента
        
    Returns:
        DynamicAgentResponse: Обновленный агент
    """
    with SessionLocal() as session:
        try:
            # Проверяем существование агента
            check_query = text("""
                SELECT id FROM dynamic_agents 
                WHERE agent_id = :agent_id
            """)
            
            result = session.execute(check_query, {"agent_id": agent_id})
            if not result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Динамический агент {agent_id} не найден"
                )
            
            # Обновляем агента
            update_query = text("""
                UPDATE dynamic_agents 
                SET name = %(name)s, description = %(description)s, instructions = %(instructions)s,
                    model_config = %(model_config)s, tools_config = %(tools_config)s,
                    knowledge_config = %(knowledge_config)s, memory_config = %(memory_config)s,
                    storage_config = %(storage_config)s, settings = %(settings)s,
                    updated_at = NOW()
                WHERE agent_id = %(agent_id)s
                RETURNING id, created_at, updated_at
            """)
            
            result = session.execute(update_query, {
                "agent_id": agent_id,
                "name": agent_data.name,
                "description": agent_data.description,
                "instructions": agent_data.instructions,
                "model_config": json.dumps(agent_data.model_config_data.model_dump()),
                "tools_config": json.dumps(agent_data.tools_config),
                "knowledge_config": json.dumps(agent_data.knowledge_config.model_dump()),
                "memory_config": json.dumps(agent_data.memory_config.model_dump()),
                "storage_config": json.dumps(agent_data.storage_config.model_dump()),
                "settings": json.dumps(agent_data.settings.model_dump())
            })
            
            row = result.fetchone()
            session.commit()
            
            # Обновляем кэш для конкретного агента
            refresh_agent_cache(agent_id)
            
            return DynamicAgentResponse(
                id=row.id,
                name=agent_data.name,
                agent_id=agent_id,
                description=agent_data.description,
                instructions=agent_data.instructions,
                model_config_data=agent_data.model_config_data,
                tools_config=agent_data.tools_config,
                knowledge_config=agent_data.knowledge_config,
                memory_config=agent_data.memory_config,
                storage_config=agent_data.storage_config,
                settings=agent_data.settings,
                is_active=True,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при обновлении динамического агента {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось обновить динамического агента {agent_id}"
            )


@dynamic_agents_router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dynamic_agent(agent_id: str):
    """
    Удаляет динамического агента (помечает как неактивного).
    
    Args:
        agent_id: ID агента для удаления
    """
    with SessionLocal() as session:
        try:
            # Проверяем существование агента
            check_query = text("""
                SELECT id FROM dynamic_agents 
                WHERE agent_id = :agent_id AND is_active = true
            """)
            
            result = session.execute(check_query, {"agent_id": agent_id})
            if not result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Активный динамический агент {agent_id} не найден"
                )
            
            # Помечаем как неактивного
            delete_query = text("""
                UPDATE dynamic_agents 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE agent_id = :agent_id
            """)
            
            session.execute(delete_query, {"agent_id": agent_id})
            session.commit()
            
            # Обновляем кэш
            refresh_agent_cache()
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при удалении динамического агента {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось удалить динамического агента {agent_id}"
            )


@dynamic_agents_router.post("/{agent_id}/activate", status_code=status.HTTP_200_OK)
async def activate_dynamic_agent(agent_id: str):
    """
    Активирует динамического агента.
    
    Args:
        agent_id: ID агента для активации
    """
    with SessionLocal() as session:
        try:
            # Активируем агента
            activate_query = text("""
                UPDATE dynamic_agents 
                SET is_active = true, updated_at = CURRENT_TIMESTAMP
                WHERE agent_id = :agent_id
            """)
            
            result = session.execute(activate_query, {"agent_id": agent_id})
            
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Динамический агент {agent_id} не найден"
                )
            
            session.commit()
            
            # Обновляем кэш
            refresh_agent_cache()
            
            return {"message": f"Агент {agent_id} успешно активирован"}
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при активации динамического агента {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось активировать динамического агента {agent_id}"
            )


@dynamic_agents_router.post("/refresh-cache", status_code=status.HTTP_200_OK)
async def refresh_agents_cache():
    """
    Обновляет кэш динамических агентов.
    """
    try:
        refresh_agent_cache()
        return {"message": "Кэш агентов успешно обновлен"}
    except Exception as e:
        logger.error(f"Ошибка при обновлении кэша агентов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить кэш агентов"
        ) 