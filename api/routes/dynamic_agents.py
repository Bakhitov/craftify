"""
API маршруты для управления динамическими агентами.
Обеспечивает CRUD операции для динамических агентов в БД.
"""
import json
from logging import getLogger
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator
from sqlalchemy import text

from db.session import SessionLocal
from agents.selector import refresh_agent_cache, get_agent_info
from agents.cache.auto_refresh import auto_cache
from agents.dynamic.agent_factory import DynamicAgentFactory
from agents.models import (
    DynamicAgentConfig,
    ModelConfig,
    StaticToolConfig,
    DynamicToolConfig,
    MCPToolConfig,
    KnowledgeConfig,
    MemoryConfig,
    StorageConfig,
    AgentSettings,
    validate_tools_config
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
    model_id: str = Field(default="gpt-4o", description="ID модели для агента")
    
    # Типизированная конфигурация инструментов
    tools_config: List[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]] = Field(
        default_factory=list, 
        description="Типизированная конфигурация инструментов"
    )
    
    # Дополнительные настройки
    max_tokens: Optional[int] = Field(default=None, description="Максимальное количество токенов")
    temperature: Optional[float] = Field(default=None, description="Температура модели")
    
    # Конфигурации (опциональные в запросе, будут заполнены дефолтами если не переданы)
    knowledge_config: Optional[dict] = Field(default_factory=dict, description="Конфигурация знаний")
    memory_config: Optional[dict] = Field(default_factory=dict, description="Конфигурация памяти")
    storage_config: Optional[dict] = Field(default_factory=dict, description="Конфигурация хранилища")
    settings: Optional[dict] = Field(default_factory=dict, description="Настройки агента")

    @validator('tools_config')
    def validate_tools_config_field(cls, v):
        """Валидация конфигурации инструментов"""
        if not isinstance(v, list):
            raise ValueError("tools_config должен быть списком")
        
        # Преобразуем словари в типизированные модели если нужно
        if v and isinstance(v[0], dict):
            return validate_tools_config(v)
        return v
    
    def get_model_config(self) -> ModelConfig:
        """Создает ModelConfig из полей запроса"""
        model_data = {
            "id": self.model_id,
            "type": "openai",  # Дефолтный тип
        }
        if self.max_tokens is not None:
            model_data["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            model_data["temperature"] = self.temperature
        
        return ModelConfig(**model_data)
    
    def get_knowledge_config(self) -> KnowledgeConfig:
        """Создает KnowledgeConfig из полей запроса"""
        return KnowledgeConfig(**(self.knowledge_config or {}))
    
    def get_memory_config(self) -> MemoryConfig:
        """Создает MemoryConfig из полей запроса"""
        return MemoryConfig(**(self.memory_config or {}))
    
    def get_storage_config(self) -> StorageConfig:
        """Создает StorageConfig из полей запроса"""
        return StorageConfig(**(self.storage_config or {}))
    
    def get_agent_settings(self) -> AgentSettings:
        """Создает AgentSettings из полей запроса"""
        return AgentSettings(**(self.settings or {}))


class DynamicAgentResponse(BaseModel):
    """Модель ответа с информацией о динамическом агенте"""
    model_config = {"populate_by_name": True}
    
    id: int
    name: str
    agent_id: str
    description: Optional[str]
    instructions: Optional[str]
    model_id: str
    
    # Используем типизированные модели
    model_config_data: ModelConfig = Field(alias="model_config")
    tools_config: List[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]]
    knowledge_config: KnowledgeConfig
    memory_config: MemoryConfig
    storage_config: StorageConfig
    settings: AgentSettings
    
    is_active: bool
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
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
                # Данные в БД уже в формате dict/list, не JSON строки
                model_config = ModelConfig(**(row.model_config if row.model_config else {}))
                agents.append(DynamicAgentResponse(
                    id=row.id,
                    name=row.name,
                    agent_id=row.agent_id,
                    description=row.description,
                    instructions=row.instructions,
                    model_id=model_config.id,  # Извлекаем model_id из model_config
                    model_config_data=model_config,
                    tools_config=row.tools_config if row.tools_config else [],
                    knowledge_config=KnowledgeConfig(**(row.knowledge_config if row.knowledge_config else {})),
                    memory_config=MemoryConfig(**(row.memory_config if row.memory_config else {})),
                    storage_config=StorageConfig(**(row.storage_config if row.storage_config else {})),
                    settings=AgentSettings(**(row.settings if row.settings else {})),
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
            
            model_config = ModelConfig(**(row.model_config if row.model_config else {}))
            response = DynamicAgentResponse(
                id=row.id,
                name=row.name,
                agent_id=row.agent_id,
                description=row.description,
                instructions=row.instructions,
                model_id=model_config.id,  # Извлекаем model_id из model_config
                model_config_data=model_config,
                tools_config=row.tools_config if row.tools_config else [],
                knowledge_config=KnowledgeConfig(**(row.knowledge_config if row.knowledge_config else {})),
                memory_config=MemoryConfig(**(row.memory_config if row.memory_config else {})),
                storage_config=StorageConfig(**(row.storage_config if row.storage_config else {})),
                settings=AgentSettings(**(row.settings if row.settings else {})),
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
            check_query = text("SELECT COUNT(*) FROM dynamic_agents WHERE agent_id = :agent_id")
            result = session.execute(check_query, {"agent_id": agent_data.agent_id})
            if result.scalar() > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Агент с ID {agent_data.agent_id} уже существует"
                )
            
            # Создаем агента
            insert_query = text("""
                INSERT INTO dynamic_agents (
                    name, agent_id, description, instructions,
                    model_config, tools_config, knowledge_config,
                    memory_config, storage_config, settings, is_active
                ) VALUES (
                    :name, :agent_id, :description, :instructions,
                    :model_config, :tools_config, :knowledge_config,
                    :memory_config, :storage_config, :settings, :is_active
                ) RETURNING id, created_at, updated_at
            """)
            
            # Создаем типизированные конфигурации
            model_config = agent_data.get_model_config()
            knowledge_config = agent_data.get_knowledge_config()
            memory_config = agent_data.get_memory_config()
            storage_config = agent_data.get_storage_config()
            settings = agent_data.get_agent_settings()
            
            result = session.execute(insert_query, {
                "name": agent_data.name,
                "agent_id": agent_data.agent_id,
                "description": agent_data.description,
                "instructions": agent_data.instructions,
                "model_config": json.dumps(model_config.model_dump()),
                "tools_config": json.dumps([tool.model_dump() if hasattr(tool, 'model_dump') else tool for tool in agent_data.tools_config]),
                "knowledge_config": json.dumps(knowledge_config.model_dump()),
                "memory_config": json.dumps(memory_config.model_dump()),
                "storage_config": json.dumps(storage_config.model_dump()),
                "settings": json.dumps(settings.model_dump()),
                "is_active": True
            })
            
            row = result.fetchone()
            session.commit()
            
            # ✅ Автоматическое обновление кэша после создания
            auto_cache.refresh_after_agent_operation(agent_data.agent_id, "create")
            
            # ✅ Уведомляем о новом агенте
            refresh_agent_cache(agent_data.agent_id)
            
            response = DynamicAgentResponse(
                id=row.id,
                name=agent_data.name,
                agent_id=agent_data.agent_id,
                description=agent_data.description,
                instructions=agent_data.instructions,
                model_id=model_config.id,
                model_config_data=model_config,
                tools_config=agent_data.tools_config,
                knowledge_config=knowledge_config,
                memory_config=memory_config,
                storage_config=storage_config,
                settings=settings,
                is_active=True,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            
            logger.info(f"Создан динамический агент: {agent_data.agent_id}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при создании динамического агента {agent_data.agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось создать динамического агента {agent_data.agent_id}"
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
            check_query = text("SELECT id FROM dynamic_agents WHERE agent_id = :agent_id")
            result = session.execute(check_query, {"agent_id": agent_id})
            if not result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Динамический агент {agent_id} не найден"
                )
            
            # Обновляем агента
            update_query = text("""
                UPDATE dynamic_agents SET
                    name = :name,
                    description = :description,
                    instructions = :instructions,
                    model_config = :model_config,
                    tools_config = :tools_config,
                    knowledge_config = :knowledge_config,
                    memory_config = :memory_config,
                    storage_config = :storage_config,
                    settings = :settings,
                    updated_at = CURRENT_TIMESTAMP
                WHERE agent_id = :agent_id
                RETURNING id, created_at, updated_at
            """)
            
            # Создаем типизированные конфигурации
            model_config = agent_data.get_model_config()
            knowledge_config = agent_data.get_knowledge_config()
            memory_config = agent_data.get_memory_config()
            storage_config = agent_data.get_storage_config()
            settings = agent_data.get_agent_settings()
            
            result = session.execute(update_query, {
                "agent_id": agent_id,
                "name": agent_data.name,
                "description": agent_data.description,
                "instructions": agent_data.instructions,
                "model_config": json.dumps(model_config.model_dump()),
                "tools_config": json.dumps([tool.model_dump() if hasattr(tool, 'model_dump') else tool for tool in agent_data.tools_config]),
                "knowledge_config": json.dumps(knowledge_config.model_dump()),
                "memory_config": json.dumps(memory_config.model_dump()),
                "storage_config": json.dumps(storage_config.model_dump()),
                "settings": json.dumps(settings.model_dump())
            })
            
            row = result.fetchone()
            session.commit()
            
            # ✅ Автоматическое обновление кэша после обновления
            auto_cache.refresh_after_agent_operation(agent_id, "update")
            
            # ✅ Уведомляем об обновлении агента
            refresh_agent_cache(agent_id)
            
            response = DynamicAgentResponse(
                id=row.id,
                name=agent_data.name,
                agent_id=agent_id,
                description=agent_data.description,
                instructions=agent_data.instructions,
                model_id=model_config.id,
                model_config_data=model_config,
                tools_config=agent_data.tools_config,
                knowledge_config=knowledge_config,
                memory_config=memory_config,
                storage_config=storage_config,
                settings=settings,
                is_active=True,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            
            logger.info(f"Обновлен динамический агент: {agent_id}")
            return response
            
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
    Удаляет динамического агента (мягкое удаление - устанавливает is_active = false).
    
    Args:
        agent_id: ID агента для удаления
    """
    with SessionLocal() as session:
        try:
            # Проверяем существование агента
            check_query = text("SELECT id FROM dynamic_agents WHERE agent_id = :agent_id AND is_active = true")
            result = session.execute(check_query, {"agent_id": agent_id})
            if not result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Активный динамический агент {agent_id} не найден"
                )
            
            # Мягкое удаление
            delete_query = text("""
                UPDATE dynamic_agents 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP 
                WHERE agent_id = :agent_id
            """)
            session.execute(delete_query, {"agent_id": agent_id})
            session.commit()
            
            # ✅ Автоматическое обновление кэша после удаления
            auto_cache.refresh_after_agent_operation(agent_id, "delete")
            
            # ✅ Уведомляем об удалении агента
            refresh_agent_cache(agent_id)
            
            logger.info(f"Удален динамический агент: {agent_id}")
            
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
    Активирует ранее деактивированного динамического агента.
    
    Args:
        agent_id: ID агента для активации
        
    Returns:
        Dict: Результат операции
    """
    with SessionLocal() as session:
        try:
            # Проверяем существование агента
            check_query = text("SELECT id FROM dynamic_agents WHERE agent_id = :agent_id")
            result = session.execute(check_query, {"agent_id": agent_id})
            if not result.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Динамический агент {agent_id} не найден"
                )
            
            # Активируем агента
            activate_query = text("""
                UPDATE dynamic_agents 
                SET is_active = true, updated_at = CURRENT_TIMESTAMP 
                WHERE agent_id = :agent_id
            """)
            result = session.execute(activate_query, {"agent_id": agent_id})
            session.commit()
            
            # ✅ Автоматическое обновление кэша после активации
            auto_cache.refresh_after_agent_operation(agent_id, "activate")
            
            # ✅ Уведомляем об активации агента
            refresh_agent_cache(agent_id)
            
            logger.info(f"Активирован динамический агент: {agent_id}")
            
            return {
                "status": "success",
                "message": f"Агент {agent_id} успешно активирован",
                "agent_id": agent_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при активации динамического агента {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось активировать динамического агента {agent_id}"
            )

# УДАЛЕНО: Ручное обновление кэша больше не нужно - кэш обновляется автоматически при CRUD операциях 
