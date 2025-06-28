"""
Единый реестр для статических и динамических агентов.
Обеспечивает изоляцию и единую точку доступа.
Использует изолированную архитектуру для совместимости с Agno.
"""
import time
from typing import Dict, List, Optional, Callable, Any
from agno.agent import Agent

# Импорты статических агентов
from agents.static.agno_assist import get_agno_assist
from agents.static.finance_agent import get_finance_agent  
from agents.static.web_agent import get_web_agent

# Импорт фабрики динамических агентов
from agents.dynamic.agent_factory import DynamicAgentFactory


class AgentRegistry:
    """
    Единый реестр для статических и динамических агентов.
    Обеспечивает изоляцию между статическими и динамическими агентами,
    используя только стандартные классы agno.
    """
    
    def __init__(self):
        # Статические агенты - определены в файлах
        self._static_agents: Dict[str, Callable] = {
            'agno_assist': get_agno_assist,
            'finance_agent': get_finance_agent,
            'web_agent': get_web_agent
        }
        
        # Кэш для динамических агентов
        self._dynamic_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 минут
        self._last_dynamic_refresh = 0
    
    def get_agent(
        self,
        agent_id: str,
        model_id: str = "gpt-4.1",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        debug_mode: bool = True
    ) -> Agent:
        """
        Получает агента (статического или динамического) с кэшированием.
        
        Args:
            agent_id: ID агента
            model_id: ID модели
            user_id: ID пользователя
            session_id: ID сессии
            debug_mode: Режим отладки
            
        Returns:
            Экземпляр Agent
            
        Raises:
            ValueError: Если агент не найден
        """
        # Импорт кэш менеджера
        from agents.cache import cache_manager
        
        # Проверяем кэш сначала
        cached_agent = cache_manager.get_agent(
            agent_id=agent_id,
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )
        
        if cached_agent:
            return cached_agent
        
        # Создаем агента
        agent = None
        
        # Сначала проверяем статических агентов
        if agent_id in self._static_agents:
            agent = self._create_static_agent(
                agent_id=agent_id,
                model_id=model_id,
                user_id=user_id,
                session_id=session_id,
                debug_mode=debug_mode
            )
        else:
            # Затем ищем в динамических агентах
            agent = self._create_dynamic_agent(
                agent_id=agent_id,
                model_id=model_id,
                user_id=user_id,
                session_id=session_id,
                debug_mode=debug_mode
            )
        
        # Кэшируем созданного агента
        if agent:
            cache_manager.set_agent(agent_id, agent, ttl=600)
        
        return agent

    def _create_static_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """
        Создает статического агента.
        
        Args:
            agent_id: ID статического агента
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр Agent или None
        """
        try:
            if agent_id in self._static_agents:
                agent_factory = self._static_agents[agent_id]
                return agent_factory(**kwargs)
            else:
                print(f"Неизвестный статический агент: {agent_id}")
                return None
                
        except ImportError as e:
            print(f"Ошибка импорта статического агента {agent_id}: {e}")
            return None
        except Exception as e:
            from agents.exceptions import handle_agent_error
            error = handle_agent_error("create", agent_id, e, {"type": "static"})
            print(f"⚠️ {error}")
            return None

    def _create_dynamic_agent(
        self, 
        agent_id: str, 
        model_id: str, 
        user_id: Optional[str], 
        session_id: Optional[str], 
        debug_mode: bool
    ) -> Optional[Agent]:
        """Создает динамического агента используя фабрику"""
        try:
            agent = DynamicAgentFactory.create_agent_from_db(
                agent_id=agent_id,
                model_id=model_id,
                user_id=user_id,
                session_id=session_id,
                debug_mode=debug_mode
            )
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
                
            return agent
        except Exception as e:
            from agents.exceptions import handle_agent_error
            error = handle_agent_error("create", agent_id, e, {"type": "dynamic"})
            print(f"⚠️ {error}")
            return None
    
    def get_available_agents(self) -> List[str]:
        """
        Возвращает список всех доступных агентов (статических и динамических) с кэшированием.
        
        Returns:
            Список ID агентов
        """
        # Импорт кэш менеджера
        from agents.cache import cache_manager
        
        # Проверяем кэш
        cached_list = cache_manager.get_agents_list()
        if cached_list:
            return cached_list
        
        # Создаем список
        static_agents = list(self._static_agents.keys())
        dynamic_agents = self._get_dynamic_agent_ids()
        all_agents = static_agents + dynamic_agents
        
        # Кэшируем результат
        cache_manager.set_agents_list(all_agents, ttl=300)
        
        return all_agents
    
    def get_static_agents(self) -> List[str]:
        """Возвращает список статических агентов"""
        return list(self._static_agents.keys())
    
    def get_dynamic_agents(self) -> List[str]:
        """Возвращает список динамических агентов"""
        return self._get_dynamic_agent_ids()
    
    def is_static_agent(self, agent_id: str) -> bool:
        """Проверяет является ли агент статическим"""
        return agent_id in self._static_agents
    
    def is_dynamic_agent(self, agent_id: str) -> bool:
        """Проверяет является ли агент динамическим"""
        return agent_id in self._get_dynamic_agent_ids()
    
    def refresh_cache(self, agent_id: Optional[str] = None):
        """
        Обновляет кэш агентов (локальный и глобальный).
        
        Args:
            agent_id: ID конкретного агента для обновления (если None, обновляются все)
        """
        # Импорт кэш менеджера
        from agents.cache import cache_manager
        
        if agent_id:
            # Удаляем конкретного агента из локального кэша
            self._dynamic_cache.pop(agent_id, None)
            # Обновляем глобальный кэш
            cache_manager.refresh_agent(agent_id)
            # Очищаем кэш конфигураций для динамических агентов
            if self.is_dynamic_agent(agent_id):
                from agents.dynamic.agent_factory import DynamicAgentFactory
                DynamicAgentFactory.clear_config_cache(agent_id)
        else:
            # Очищаем локальный кэш
            self._dynamic_cache.clear()
            self._last_dynamic_refresh = 0
            # Обновляем глобальный кэш
            cache_manager.refresh_all()
            # Очищаем весь кэш конфигураций
            from agents.dynamic.agent_factory import DynamicAgentFactory
            DynamicAgentFactory.clear_config_cache()

    def _get_dynamic_agent_ids(self) -> List[str]:
        """
        Получает список ID динамических агентов с кэшированием.
        
        Returns:
            Список ID динамических агентов
        """
        current_time = time.time()
        
        # Проверяем нужно ли обновить кэш
        if (current_time - self._last_dynamic_refresh) > self._cache_ttl:
            try:
                dynamic_ids = DynamicAgentFactory.get_dynamic_agent_ids()
                self._dynamic_cache['agent_ids'] = {
                    'data': dynamic_ids,
                    'timestamp': current_time
                }
                self._last_dynamic_refresh = current_time
                return dynamic_ids
            except Exception as e:
                print(f"Ошибка при обновлении списка динамических агентов: {e}")
                # Возвращаем данные из кэша если есть
                if 'agent_ids' in self._dynamic_cache:
                    return self._dynamic_cache['agent_ids']['data']
                return []
        
        # Возвращаем данные из кэша
        if 'agent_ids' in self._dynamic_cache:
            return self._dynamic_cache['agent_ids']['data']
        
        return []
    
    def get_agent_info(self, agent_id: str) -> Dict[str, any]:
        """
        Получает информацию об агенте.
        
        Args:
            agent_id: ID агента
            
        Returns:
            Словарь с информацией об агенте
        """
        if self.is_static_agent(agent_id):
            return {
                "agent_id": agent_id,
                "type": "static",
                "source": "file",
                "editable": False
            }
        elif self.is_dynamic_agent(agent_id):
            return {
                "agent_id": agent_id,
                "type": "dynamic", 
                "source": "database",
                "editable": True
            }
        else:
            return {
                "agent_id": agent_id,
                "type": "unknown",
                "source": "none",
                "editable": False
            }

    def get_static_agent_details(self, agent_id: str) -> Dict[str, any]:
        """
        Получает детальную информацию о статическом агенте с кэшированием.
        
        Args:
            agent_id: ID статического агента
            
        Returns:
            Словарь с полной информацией о статическом агенте
        """
        if not self.is_static_agent(agent_id):
            raise ValueError(f"Agent {agent_id} is not a static agent")
        
        # Импорт кэш менеджера
        from agents.cache import cache_manager
        
        # Проверяем кэш сначала
        cache_key = f"static_agent_details:{agent_id}"
        cached_details = cache_manager.get(cache_key)
        if cached_details:
            return cached_details
        
        try:
            # Создаем экземпляр агента для извлечения конфигурации
            agent = self._create_static_agent(agent_id, debug_mode=False)
            if not agent:
                raise ValueError(f"Failed to create static agent {agent_id}")
            
            # Извлекаем основную информацию
            details = {
                "agent_id": agent_id,
                "name": getattr(agent, 'name', agent_id),
                "description": getattr(agent, 'description', None),
                "instructions": getattr(agent, 'instructions', None),
                "model_id": getattr(agent.model, 'id', 'gpt-4.1') if hasattr(agent, 'model') else 'gpt-4.1',
                "agent_type": "static",
                "editable": False,
                "is_active": True,
                "source_file": f"agents/static/{agent_id}.py"
            }
            
            # Извлекаем конфигурацию модели
            model_config = {
                "type": "openai",
                "id": details["model_id"],
                "temperature": 0.7,
                "max_tokens": None,
                "top_p": None,
                "frequency_penalty": None,
                "presence_penalty": None
            }
            
            # Пытаемся извлечь параметры модели если они есть
            if hasattr(agent, 'model') and agent.model:
                if hasattr(agent.model, 'temperature'):
                    model_config["temperature"] = agent.model.temperature
                if hasattr(agent.model, 'max_tokens'):
                    model_config["max_tokens"] = agent.model.max_tokens
                if hasattr(agent.model, 'top_p'):
                    model_config["top_p"] = agent.model.top_p
            
            details["model_config"] = model_config
            
            # Извлекаем конфигурацию инструментов
            tools_config = []
            if hasattr(agent, 'tools') and agent.tools:
                for tool in agent.tools:
                    tool_class_name = tool.__class__.__name__
                    tool_module = tool.__class__.__module__
                    tools_config.append({
                        "type": "static",
                        "import_path": f"{tool_module}.{tool_class_name}",
                        "init_params": {}
                    })
            
            details["tools_config"] = tools_config
            
            # Конфигурация знаний
            knowledge_config = {
                "enabled": bool(hasattr(agent, 'knowledge') and agent.knowledge),
                "type": "url",
                "sources": [],
                "table_name": "knowledge",
                "db_schema": "public",
                "search_type": "hybrid",
                "embedder_model": "text-embedding-3-small"
            }
            
            if hasattr(agent, 'knowledge') and agent.knowledge:
                # Пытаемся извлечь больше информации о знаниях
                if hasattr(agent.knowledge, 'urls'):
                    knowledge_config["sources"] = getattr(agent.knowledge, 'urls', [])
            
            details["knowledge_config"] = knowledge_config
            
            # Конфигурация памяти
            memory_config = {
                "enabled": bool(hasattr(agent, 'memory') and agent.memory),
                "type": "postgres",
                "memory_model_config": None,
                "table_name": "user_memories",
                "db_schema": "public",
                "delete_memories": True,
                "clear_memories": True
            }
            
            details["memory_config"] = memory_config
            
            # Конфигурация хранилища
            storage_config = {
                "enabled": bool(hasattr(agent, 'storage') and agent.storage),
                "type": "postgres",
                "table_name": "sessions",
                "db_schema": "public",
                "db_url": None
            }
            
            details["storage_config"] = storage_config
            
            # Настройки агента
            settings = {
                "name": getattr(agent, 'name', None),
                "introduction": None,
                "user_id": getattr(agent, 'user_id', None),
                "session_name": None,
                "session_state": None,
                "search_previous_sessions_history": False,
                "num_history_sessions": None,
                "context": None,
                "add_context": False,
                "resolve_context": True,
                "enable_agentic_memory": bool(hasattr(agent, 'memory') and agent.memory),
                "enable_user_memories": False,
                "add_memory_references": None,
                "enable_session_summaries": False,
                "add_session_summary_references": None,
                "add_history_to_messages": getattr(agent, 'add_history_to_messages', False),
                "debug_mode": getattr(agent, 'debug_mode', False),
                "monitoring": getattr(agent, 'monitoring', False),
                "output_model": None,
                "stream": False
            }
            
            details["settings"] = settings
            
            # Кэшируем результат на 30 минут (статические агенты редко меняются)
            cache_manager.set(cache_key, details, ttl=1800)
            
            return details
            
        except Exception as e:
            print(f"Ошибка при получении деталей статического агента {agent_id}: {e}")
            raise e

    def get_static_agent_basic_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Быстрое получение базовой информации о статическом агенте без создания объекта Agent.
        Оптимизация для list_agents() - избегаем N+1 проблему.
        """
        if not self.is_static_agent(agent_id):
            return {}
        
        # Базовая информация из статической конфигурации
        basic_info = {
            "agent_id": agent_id,
            "agent_type": "static",
            "source_file": f"agents/static/{agent_id}.py",
            "editable": False,
            "is_active": True,
            "created_at": None,
            "updated_at": None
        }
        
        # Добавляем специфичную информацию для каждого агента
        if agent_id == "agno_assist":
            basic_info.update({
                "name": "Agno Assist",
                "description": "Advanced AI Agent specializing in Agno framework development",
                "model_id": "gpt-4.1",
                "tools_config": [{"type": "static", "import_path": "agno.tools.duckduckgo.DuckDuckGoTools"}],
                "knowledge_config": {"enabled": True, "type": "url", "sources": ["https://docs.agno.com/llms-full.txt"]},
                "memory_config": {"enabled": True, "type": "postgres"},
                "storage_config": {"enabled": True, "type": "postgres"}
            })
        elif agent_id == "finance_agent":
            basic_info.update({
                "name": "Finance Agent", 
                "description": "Financial analysis and market data agent",
                "model_id": "gpt-4.1",
                "tools_config": [{"type": "static", "import_path": "agno.tools.yfinance.YFinanceTools"}],
                "knowledge_config": {"enabled": False},
                "memory_config": {"enabled": True, "type": "postgres"},
                "storage_config": {"enabled": True, "type": "postgres"}
            })
        elif agent_id == "web_agent":
            basic_info.update({
                "name": "Web Agent",
                "description": "Web browsing and search agent", 
                "model_id": "gpt-4.1",
                "tools_config": [
                    {"type": "static", "import_path": "agno.tools.duckduckgo.DuckDuckGoTools"},
                    {"type": "static", "import_path": "agno.tools.newspaper4k.Newspaper4kTools"}
                ],
                "knowledge_config": {"enabled": False},
                "memory_config": {"enabled": True, "type": "postgres"},
                "storage_config": {"enabled": True, "type": "postgres"}
            })
        else:
            # Fallback для неизвестных агентов
            basic_info.update({
                "name": agent_id.replace('_', ' ').title(),
                "description": f"Static agent: {agent_id}",
                "model_id": "gpt-4.1",
                "tools_config": [],
                "knowledge_config": {"enabled": False},
                "memory_config": {"enabled": False},
                "storage_config": {"enabled": True, "type": "postgres"}
            })
        
        return basic_info


# Глобальный экземпляр реестра
agent_registry = AgentRegistry() 