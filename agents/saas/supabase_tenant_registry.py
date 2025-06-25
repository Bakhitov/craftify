"""
Tenant-aware реестр агентов с интеграцией Supabase Auth.
Обеспечивает мультитенантность и горячую перезагрузку для SaaS платформы.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import logging

from agno.agent import Agent
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from db.session import SessionLocal, db_url
from agents.dynamic.agent_factory import DynamicAgentFactory
from agents.models.saas_models import TenantConfig, AgentChangeEvent, HotReloadConfig

# Импорты статических агентов
from agents.static.agno_assist import get_agno_assist
from agents.static.finance_agent import get_finance_agent  
from agents.static.web_agent import get_web_agent

logger = logging.getLogger(__name__)


class SupabaseTenantRegistry:
    """
    Tenant-aware реестр агентов с интеграцией Supabase Auth.
    Поддерживает горячую перезагрузку и мультитенантность.
    """
    
    def __init__(self, hot_reload_config: HotReloadConfig = None):
        # Глобальные статические агенты (доступны всем тенантам)
        self._global_static_agents: Dict[str, Callable] = {
            'agno_assist': get_agno_assist,
            'finance_agent': get_finance_agent,
            'web_agent': get_web_agent
        }
        
        # Кэш динамических агентов по тенантам: {tenant_id: {agent_id: config}}
        self._tenant_dynamic_cache: Dict[str, Dict[str, Dict]] = {}
        
        # Кэш конфигураций тенантов: {tenant_id: TenantConfig}
        self._tenant_configs: Dict[str, TenantConfig] = {}
        
        # Конфигурация горячей перезагрузки
        self._hot_reload_config = hot_reload_config or HotReloadConfig()
        
        # Метаданные кэша
        self._cache_timestamps: Dict[str, datetime] = {}
        self._last_global_refresh = datetime.utcnow()
        
        # Очередь событий для горячей перезагрузки
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._notification_task: Optional[asyncio.Task] = None
        
        # Инициализация
        if self._hot_reload_config.enabled:
            self._start_notification_listener()
    
    def get_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        model_id: str = "gpt-4.1",
        session_id: Optional[str] = None,
        debug_mode: bool = True
    ) -> Agent:
        """
        Получает агента с учетом тенанта и прав доступа.
        
        Args:
            agent_id: ID агента
            tenant_id: ID тенанта (из Supabase Auth JWT)
            user_id: ID пользователя (из Supabase Auth JWT)
            model_id: ID модели
            session_id: ID сессии
            debug_mode: Режим отладки
            
        Returns:
            Экземпляр Agent
            
        Raises:
            ValueError: Если агент не найден или нет доступа
        """
        # 1. Проверяем лимиты тенанта
        if not self._check_tenant_limits(tenant_id, user_id):
            raise ValueError(f"Tenant {tenant_id} exceeded usage limits")
        
        # 2. Проверяем глобальные статические агенты
        if agent_id in self._global_static_agents:
            return self._create_static_agent(
                agent_id=agent_id,
                tenant_id=tenant_id,
                user_id=user_id,
                model_id=model_id,
                session_id=session_id,
                debug_mode=debug_mode
            )
        
        # 3. Проверяем динамические агенты тенанта
        return self._get_tenant_dynamic_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            model_id=model_id,
            session_id=session_id,
            debug_mode=debug_mode
        )
    
    def get_available_agents(self, tenant_id: str, user_id: str) -> List[str]:
        """
        Возвращает список доступных агентов для тенанта.
        
        Args:
            tenant_id: ID тенанта
            user_id: ID пользователя
            
        Returns:
            Список ID агентов
        """
        agents = []
        
        # Глобальные статические агенты (доступны всем)
        agents.extend(self._global_static_agents.keys())
        
        # Динамические агенты тенанта
        tenant_agents = self._get_tenant_agent_ids(tenant_id)
        agents.extend(tenant_agents)
        
        # Публичные агенты других тенантов
        public_agents = self._get_public_agent_ids(exclude_tenant=tenant_id)
        agents.extend(public_agents)
        
        return list(set(agents))  # Убираем дубликаты
    
    async def handle_agent_change(self, event: AgentChangeEvent):
        """
        Обрабатывает событие изменения агента для горячей перезагрузки.
        
        Args:
            event: Событие изменения агента
        """
        try:
            tenant_id = event.tenant_id
            agent_id = event.agent_id
            
            logger.info(f"Processing agent change event: {event.event_type} for {tenant_id}:{agent_id}")
            
            # Инвалидируем кэш для агента
            if tenant_id in self._tenant_dynamic_cache:
                self._tenant_dynamic_cache[tenant_id].pop(agent_id, None)
                self._cache_timestamps.pop(f"{tenant_id}:{agent_id}", None)
            
            # Для событий удаления/деактивации дополнительно очищаем кэш
            if event.event_type in ['deleted', 'deactivated']:
                logger.info(f"Agent {tenant_id}:{agent_id} removed from cache")
            else:
                logger.info(f"Agent {tenant_id}:{agent_id} cache invalidated for reload")
                
        except Exception as e:
            logger.error(f"Error handling agent change event: {e}")
    
    def _create_static_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: Optional[str],
        model_id: str,
        session_id: Optional[str],
        debug_mode: bool
    ) -> Agent:
        """Создает статического агента с контекстом тенанта"""
        agent_factory = self._global_static_agents[agent_id]
        
        # Создаем агента с базовыми параметрами
        agent = agent_factory(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )
        
        # Добавляем контекст тенанта в состояние сессии
        if not agent.session_state:
            agent.session_state = {}
        
        agent.session_state.update({
            'tenant_id': tenant_id,
            'user_id': user_id,
            'agent_type': 'static',
            'agent_source': 'platform'
        })
        
        return agent
    
    def _get_tenant_dynamic_agent(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: Optional[str],
        model_id: str,
        session_id: Optional[str],
        debug_mode: bool
    ) -> Agent:
        """Получает динамического агента тенанта с кэшированием"""
        cache_key = f"{tenant_id}:{agent_id}"
        
        # Проверяем кэш
        if self._is_cache_valid(cache_key):
            cached_config = self._tenant_dynamic_cache[tenant_id][agent_id]
            return self._create_agent_from_cached_config(
                cached_config, model_id, user_id, session_id, debug_mode
            )
        
        # Загружаем из БД
        agent_config = self._load_tenant_agent_from_db(agent_id, tenant_id)
        if not agent_config:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")
        
        # Проверяем права доступа
        if not self._check_agent_access(agent_config, tenant_id, user_id):
            raise ValueError(f"Access denied to agent {agent_id}")
        
        # Кэшируем конфигурацию
        if tenant_id not in self._tenant_dynamic_cache:
            self._tenant_dynamic_cache[tenant_id] = {}
        
        self._tenant_dynamic_cache[tenant_id][agent_id] = agent_config
        self._cache_timestamps[cache_key] = datetime.utcnow()
        
        # Создаем агента
        return DynamicAgentFactory.create_agent_from_db(
            agent_id=agent_id,
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode,
            tenant_context={
                'tenant_id': tenant_id,
                'user_id': user_id,
                'agent_type': 'dynamic'
            }
        )
    
    def _load_tenant_agent_from_db(self, agent_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Загружает конфигурацию агента из БД с учетом тенанта"""
        with SessionLocal() as session:
            try:
                query = text("""
                    SELECT name, agent_id, description, instructions, 
                           model_config, tools_config, knowledge_config, 
                           memory_config, storage_config, settings,
                           is_public, shared_with_tenants, created_by
                    FROM dynamic_agents 
                    WHERE agent_id = :agent_id 
                    AND (
                        tenant_id = :tenant_id 
                        OR is_public = true 
                        OR :tenant_id = ANY(shared_with_tenants)
                    )
                    AND is_active = true
                """)
                
                result = session.execute(query, {
                    "agent_id": agent_id,
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    return {
                        "name": row.name,
                        "agent_id": row.agent_id,
                        "description": row.description,
                        "instructions": row.instructions,
                        "model_config": row.model_config or {},
                        "tools_config": row.tools_config or [],
                        "knowledge_config": row.knowledge_config or {},
                        "memory_config": row.memory_config or {},
                        "storage_config": row.storage_config or {},
                        "settings": row.settings or {},
                        "is_public": row.is_public,
                        "shared_with_tenants": row.shared_with_tenants or [],
                        "created_by": row.created_by
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Error loading agent {agent_id} for tenant {tenant_id}: {e}")
                return None
    
    def _check_tenant_limits(self, tenant_id: str, user_id: Optional[str]) -> bool:
        """Проверяет лимиты тенанта"""
        tenant_config = self._get_tenant_config(tenant_id)
        if not tenant_config:
            return False
        
        # Здесь можно добавить проверки:
        # - Количество активных агентов
        # - Rate limiting
        # - Квоты на использование
        
        return True
    
    def _check_agent_access(self, agent_config: Dict[str, Any], tenant_id: str, user_id: Optional[str]) -> bool:
        """Проверяет права доступа к агенту"""
        # Публичные агенты доступны всем
        if agent_config.get('is_public', False):
            return True
        
        # Агенты, явно расшаренные с тенантом
        shared_tenants = agent_config.get('shared_with_tenants', [])
        if tenant_id in shared_tenants:
            return True
        
        # Собственные агенты тенанта (проверяем через БД)
        return self._is_agent_owned_by_tenant(agent_config['agent_id'], tenant_id)
    
    def _get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Получает конфигурацию тенанта"""
        if tenant_id in self._tenant_configs:
            return self._tenant_configs[tenant_id]
        
        # Загружаем из БД или создаем дефолтную
        tenant_config = self._load_tenant_config_from_db(tenant_id)
        if tenant_config:
            self._tenant_configs[tenant_id] = tenant_config
            return tenant_config
        
        # Создаем дефолтную конфигурацию для нового тенанта
        default_config = TenantConfig(
            tenant_id=tenant_id,
            name=f"Tenant {tenant_id}",
            subscription_tier="free"
        )
        self._tenant_configs[tenant_id] = default_config
        return default_config
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверяет актуальность кэша"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        ttl = timedelta(seconds=self._hot_reload_config.cache_ttl_seconds)
        
        return datetime.utcnow() - cache_time < ttl
    
    def _start_notification_listener(self):
        """Запускает слушатель уведомлений PostgreSQL"""
        if self._hot_reload_config.enable_db_notifications:
            self._notification_task = asyncio.create_task(self._listen_for_changes())
    
    async def _listen_for_changes(self):
        """Слушает уведомления об изменениях в БД"""
        try:
            # Здесь будет реализация PostgreSQL LISTEN/NOTIFY
            # или интеграция с Supabase Realtime
            while True:
                # Имитация получения уведомления
                await asyncio.sleep(1)
                
                # Обработка событий из очереди
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                    await self.handle_agent_change(event)
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"Notification listener error: {e}")
    
    def _get_tenant_agent_ids(self, tenant_id: str) -> List[str]:
        """Получает список ID агентов тенанта"""
        with SessionLocal() as session:
            try:
                query = text("""
                    SELECT agent_id 
                    FROM dynamic_agents 
                    WHERE tenant_id = :tenant_id AND is_active = true
                """)
                
                result = session.execute(query, {"tenant_id": tenant_id})
                return [row.agent_id for row in result.fetchall()]
                
            except Exception as e:
                logger.error(f"Error getting tenant agent IDs: {e}")
                return []
    
    def _get_public_agent_ids(self, exclude_tenant: str) -> List[str]:
        """Получает список ID публичных агентов"""
        with SessionLocal() as session:
            try:
                query = text("""
                    SELECT agent_id 
                    FROM dynamic_agents 
                    WHERE is_public = true 
                    AND tenant_id != :exclude_tenant 
                    AND is_active = true
                """)
                
                result = session.execute(query, {"exclude_tenant": exclude_tenant})
                return [row.agent_id for row in result.fetchall()]
                
            except Exception as e:
                logger.error(f"Error getting public agent IDs: {e}")
                return []
    
    def invalidate_tenant_cache(self, tenant_id: str, agent_id: Optional[str] = None):
        """Инвалидирует кэш тенанта"""
        if agent_id:
            # Инвалидируем конкретного агента
            cache_key = f"{tenant_id}:{agent_id}"
            if tenant_id in self._tenant_dynamic_cache:
                self._tenant_dynamic_cache[tenant_id].pop(agent_id, None)
            self._cache_timestamps.pop(cache_key, None)
        else:
            # Инвалидируем всех агентов тенанта
            self._tenant_dynamic_cache.pop(tenant_id, None)
            keys_to_remove = [k for k in self._cache_timestamps.keys() if k.startswith(f"{tenant_id}:")]
            for key in keys_to_remove:
                self._cache_timestamps.pop(key, None)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        total_cached_agents = sum(len(agents) for agents in self._tenant_dynamic_cache.values())
        
        return {
            "total_tenants_cached": len(self._tenant_dynamic_cache),
            "total_cached_agents": total_cached_agents,
            "cache_timestamps_count": len(self._cache_timestamps),
            "hot_reload_enabled": self._hot_reload_config.enabled,
            "cache_ttl_seconds": self._hot_reload_config.cache_ttl_seconds
        }


# Глобальный экземпляр реестра
supabase_tenant_registry = SupabaseTenantRegistry() 