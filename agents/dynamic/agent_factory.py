"""
Оптимизированная фабрика для создания динамических агентов из БД.
Принципы: батчевые операции, кэширование, минимум БД запросов.
"""
import json
from typing import Optional, Dict, Any, List, Union
from sqlalchemy import text

from agno.agent import Agent, AgentKnowledge
from agno.models.openai import OpenAIChat
from agno.models.base import Model
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.tools.function import Function
from agno.tools.toolkit import Toolkit
from agno.knowledge.url import UrlKnowledge
from agno.knowledge.document import DocumentKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType

from agents.dynamic.tool_factory import DynamicToolFactory
from agents.models import (
    ModelConfig, MemoryConfig, StorageConfig, KnowledgeConfig, AgentSettings
)
from agents.factory.agno_compatibility_adapter import agno_adapter
from db.session import SessionLocal
from db.url import get_db_url

# URL базы данных
db_url = get_db_url()
print(f"🔗 DynamicAgentFactory: db_url = {db_url}")

# Простой кэш конфигураций для производительности
_config_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 300  # 5 минут


class DynamicAgentFactory:
    """
    Оптимизированная фабрика для создания динамических агентов.
    - Батчевые операции БД
    - Кэширование конфигураций
    - Упрощенные параметры агентов
    - Быстрое создание
    """
    
    @staticmethod
    def create_agent_from_db(
        agent_id: str,
        model_id: str = "gpt-4.1",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        debug_mode: bool = True
    ) -> Optional[Agent]:
        """
        Быстро создает агента из БД с кэшированием конфигурации.
        """
        try:
            # Получаем конфигурацию (с кэшированием)
            agent_config = DynamicAgentFactory._get_agent_config_cached(agent_id)
            if not agent_config:
                return None
            
            # Создаем основные компоненты
            model = DynamicAgentFactory._create_model_fast(model_id)
            tools = DynamicAgentFactory._create_tools_fast(agent_config.get('tools_config', []))
            
            # Создаем агента с ТОЛЬКО необходимыми параметрами
            agent_params = {
                'name': agent_config['name'],
                'agent_id': agent_config['agent_id'],
                'model': model,
                'user_id': user_id,
                'session_id': session_id,
                'description': agent_config.get('description'),
                'instructions': agent_config.get('instructions'),
                'tools': tools,
                'debug_mode': debug_mode,
                'markdown': True,  # Всегда включаем markdown
                'add_datetime_to_instructions': True,  # Полезно для контекста
            }
            
            # Получаем конфигурации из БД
            memory_config = agent_config.get('memory_config', {})
            storage_config = agent_config.get('storage_config', {})
            knowledge_config = agent_config.get('knowledge_config', {})
            settings = agent_config.get('settings', {})
            
            # Memory - создаем если включена в конфигурации
            if memory_config.get('enabled', False):
                memory = DynamicAgentFactory._create_memory_from_config(model_id, memory_config)
                if memory:
                    agent_params['memory'] = memory
                    agent_params['enable_agentic_memory'] = True
            
            # Storage - создаем если включено в конфигурации (по умолчанию включено)
            if storage_config.get('enabled', True):
                storage = DynamicAgentFactory._create_storage_from_config(storage_config)
                if storage:
                    agent_params['storage'] = storage
                    # Включаем history если storage есть
                    agent_params['add_history_to_messages'] = settings.get('add_history_to_messages', True)
                    agent_params['num_history_runs'] = settings.get('num_history_runs', 3)
                    agent_params['read_chat_history'] = settings.get('read_chat_history', True)
            
            # Knowledge - создаем если включена в конфигурации
            if knowledge_config.get('enabled', False):
                knowledge = DynamicAgentFactory._create_knowledge_fast(knowledge_config)
                if knowledge:
                    agent_params['knowledge'] = knowledge
                    agent_params['search_knowledge'] = True
                    agent_params['add_references'] = settings.get('add_references', False)
            
            # Применяем дополнительные настройки из settings
            for key, value in settings.items():
                if key in ['debug_mode', 'markdown', 'add_datetime_to_instructions', 
                          'add_location_to_instructions', 'show_tool_calls', 'tool_call_limit',
                          'reasoning', 'reasoning_min_steps', 'reasoning_max_steps',
                          'retries', 'delay_between_retries', 'exponential_backoff']:
                    agent_params[key] = value
            
            # Создаем агента через адаптер совместимости
            return agno_adapter.create_agent_safely(**agent_params)
            
        except Exception as e:
            print(f"⚠️ Ошибка создания агента {agent_id}: {e}")
            return None
    
    @staticmethod
    def _get_agent_config_cached(agent_id: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию агента с кэшированием"""
        import time
        
        # Проверяем кэш
        if agent_id in _config_cache:
            config_data = _config_cache[agent_id]
            if time.time() - config_data['cached_at'] < _cache_ttl:
                return config_data['config']
        
        # Загружаем из БД
        try:
            with SessionLocal() as session:
                query = text("""
                    SELECT agent_id, name, description, instructions,
                           model_config, tools_config, memory_config, 
                           storage_config, knowledge_config, settings
                    FROM dynamic_agents 
                    WHERE agent_id = :agent_id AND is_active = true
                """)
                result = session.execute(query, {"agent_id": agent_id})
                row = result.fetchone()
                
                if not row:
                    return None
                
                # Создаем конфигурацию (данные уже в JSON формате из БД)
                config = {
                    'agent_id': row.agent_id,
                    'name': row.name,
                    'description': row.description,
                    'instructions': row.instructions,
                    'model_config': row.model_config if isinstance(row.model_config, dict) else json.loads(row.model_config or '{}'),
                    'tools_config': row.tools_config if isinstance(row.tools_config, list) else json.loads(row.tools_config or '[]'),
                    'memory_config': row.memory_config if isinstance(row.memory_config, dict) else json.loads(row.memory_config or '{}'),
                    'storage_config': row.storage_config if isinstance(row.storage_config, dict) else json.loads(row.storage_config or '{}'),
                    'knowledge_config': row.knowledge_config if isinstance(row.knowledge_config, dict) else json.loads(row.knowledge_config or '{}'),
                    'settings': row.settings if isinstance(row.settings, dict) else json.loads(row.settings or '{}')
                }
                
                # Кэшируем
                _config_cache[agent_id] = {
                    'config': config,
                    'cached_at': time.time()
                }
                
                return config
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации агента {agent_id}: {e}")
            return None
    
    @staticmethod
    def _create_model_fast(model_id: str) -> Model:
        """Быстрое создание модели"""
        return OpenAIChat(id=model_id)
    
    @staticmethod
    def _create_tools_fast(tools_config: List[Union[Dict[str, Any], "StaticToolConfig", "DynamicToolConfig", "MCPToolConfig"]]) -> List[Union[Function, Toolkit]]:
        """Быстрое создание инструментов"""
        tools = []
        
        for tool_config in tools_config[:10]:  # Ограничиваем 10 инструментами
            try:
                # Преобразуем типизированные модели в словари для совместимости
                if hasattr(tool_config, 'dict'):
                    config_dict = tool_config.dict()
                else:
                    config_dict = tool_config
                
                tool_type = config_dict.get('type', 'static')
                
                if tool_type == 'static':
                    tool = DynamicAgentFactory._import_static_tool_fast(
                        config_dict.get('import_path', ''),
                        config_dict.get('init_params', {})
                    )
                    if tool:
                        tools.append(tool)
                
                elif tool_type == 'dynamic':
                    tool = DynamicToolFactory.create_tool_from_db(
                        config_dict.get('tool_id', '')
                    )
                    if tool:
                        tools.append(tool)
                
            except Exception as e:
                print(f"⚠️ Ошибка создания инструмента: {e}")
                continue
        
        return tools
    
    @staticmethod
    def _import_static_tool_fast(import_path: str, init_params: Dict[str, Any]) -> Optional[Union[Function, Toolkit]]:
        """Быстрый импорт статического инструмента"""
        try:
            if not import_path:
                return None
            
            # Простые популярные инструменты
            if 'DuckDuckGoTools' in import_path:
                from agno.tools.duckduckgo import DuckDuckGoTools
                return DuckDuckGoTools()
            
            elif 'CalculatorTools' in import_path:
                from agno.tools.calculator import CalculatorTools
                return CalculatorTools()
            
            elif 'SleepTools' in import_path:
                from agno.tools.sleep import SleepTools
                return SleepTools()
            
            elif 'WeatherToolkit' in import_path:
                from agents.tools.weather_toolkit import WeatherToolkit
                return WeatherToolkit()
            
            # Общий импорт для других инструментов
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)
            
            return tool_class(**init_params) if init_params else tool_class()
            
        except Exception as e:
            print(f"⚠️ Ошибка импорта инструмента {import_path}: {e}")
            return None
    
    @staticmethod
    def _create_memory_from_config(model_id: str, memory_config: Dict[str, Any]) -> Optional[Memory]:
        """Создание памяти на основе конфигурации"""
        try:
            # Получаем db_url из конфигурации или используем глобальный
            memory_db_url = memory_config.get("db_url") or db_url
            
            if not memory_db_url:
                print(f"⚠️ Ошибка: db_url не найден в конфигурации memory и глобальном значении")
                return None
            
            return Memory(
                model=OpenAIChat(id=model_id),
                db=PostgresMemoryDb(
                    table_name=memory_config.get("table_name", "user_memories"),
                    schema=memory_config.get("db_schema", "public"), 
                    db_url=memory_db_url
                ),
                delete_memories=memory_config.get("delete_memories", True),
                clear_memories=memory_config.get("clear_memories", True)
            )
        except Exception as e:
            print(f"⚠️ Ошибка создания памяти: {e}")
            print(f"   memory_config: {memory_config}")
            print(f"   db_url: {db_url}")
            return None
    
    @staticmethod
    def _create_storage_from_config(storage_config: Dict[str, Any]) -> Optional[PostgresAgentStorage]:
        """Создание хранилища на основе конфигурации"""
        try:
            # Получаем db_url из конфигурации или используем глобальный
            storage_db_url = storage_config.get("db_url") or db_url
            
            if not storage_db_url:
                print(f"⚠️ Ошибка: db_url не найден в конфигурации storage и глобальном значении")
                return None
            
            return PostgresAgentStorage(
                table_name=storage_config.get("table_name", "sessions"),
                schema=storage_config.get("db_schema", "public"),
                db_url=storage_db_url
            )
        except Exception as e:
            print(f"⚠️ Ошибка создания хранилища: {e}")
            print(f"   storage_config: {storage_config}")
            print(f"   db_url: {db_url}")
            return None
    
    @staticmethod
    def _create_knowledge_fast(knowledge_config: Dict[str, Any]) -> Optional[AgentKnowledge]:
        """Быстрое создание базы знаний"""
        try:
            if not knowledge_config.get('enabled', False):
                return None
            
            sources = knowledge_config.get('sources', [])
            if not sources:
                return None
            
            # Простая URL база знаний
            if knowledge_config.get('type') == 'url':
                return UrlKnowledge(
                    urls=sources[:5],  # Ограничиваем 5 URL
                    vector_db=PgVector(
                        db_url=db_url,
                        table_name=knowledge_config.get('table_name', 'knowledge'),
                        schema="public",
                        search_type=SearchType.hybrid,
                        embedder=OpenAIEmbedder(id="text-embedding-3-small")
                    )
                )
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_dynamic_agent_ids() -> List[str]:
        """Быстрое получение списка ID динамических агентов"""
        try:
            with SessionLocal() as session:
                query = text("""
                    SELECT agent_id 
                    FROM dynamic_agents 
                    WHERE is_active = true 
                    ORDER BY name
                    LIMIT 100
                """)
                result = session.execute(query)
                return [row.agent_id for row in result.fetchall()]
        except Exception as e:
            print(f"⚠️ Ошибка получения списка агентов: {e}")
            return []
    
    @staticmethod
    def get_agents_batch(agent_ids: List[str]) -> List[Dict[str, Any]]:
        """Батчевое получение конфигураций агентов"""
        try:
            with SessionLocal() as session:
                # ОДИН запрос для всех агентов
                query = text("""
                    SELECT agent_id, name, description, instructions,
                           model_config, tools_config, settings
                    FROM dynamic_agents 
                    WHERE agent_id = ANY(:agent_ids) AND is_active = true
                """)
                result = session.execute(query, {"agent_ids": agent_ids})
                
                configs = []
                for row in result.fetchall():
                    configs.append({
                        'agent_id': row.agent_id,
                        'name': row.name,
                        'description': row.description,
                        'instructions': row.instructions,
                        'model_config': row.model_config if isinstance(row.model_config, dict) else json.loads(row.model_config or '{}'),
                        'tools_config': row.tools_config if isinstance(row.tools_config, list) else json.loads(row.tools_config or '[]'),
                        'settings': row.settings if isinstance(row.settings, dict) else json.loads(row.settings or '{}')
                    })
                
                return configs
                
        except Exception as e:
            print(f"⚠️ Ошибка батчевого получения агентов: {e}")
            return []
    
    @staticmethod
    def clear_config_cache(agent_id: Optional[str] = None):
        """Очистка кэша конфигураций"""
        global _config_cache
        if agent_id:
            _config_cache.pop(agent_id, None)
        else:
            _config_cache.clear() 