import time
from typing import Dict, List, Optional
from agno.playground import Playground

from agents.static.agno_assist import get_agno_assist
from agents.static.finance_agent import get_finance_agent
from agents.static.web_agent import get_web_agent
from agents.dynamic.agent_factory import DynamicAgentFactory
from agents.cache import cache_manager
from db.session import SessionLocal
from sqlalchemy import text

######################################################
## Оптимизированный Playground Manager
######################################################

class OptimizedPlaygroundManager:
    """
    Оптимизированный менеджер playground для максимальной производительности.
    Принципы:
    - Статические агенты создаются ОДИН раз и кэшируются
    - Динамические агенты загружаются батчевым запросом
    - Инкрементальное обновление только изменившихся агентов
    - Единый кэш без дублирования
    """
    
    def __init__(self):
        self._static_agents_cache: Dict = {}
        self._playground_instance: Optional[Playground] = None
        self._last_update = 0
        self._cache_ttl = 300  # 5 минут
    
    def _get_static_agents(self) -> List:
        """Получает статических агентов с кэшированием (создаются ОДИН раз)"""
        if not self._static_agents_cache:
            try:
                print("🔄 Создание статических агентов (один раз)...")
                self._static_agents_cache = {
                    'web_agent': get_web_agent(debug_mode=True),
                    'agno_assist': get_agno_assist(debug_mode=True), 
                    'finance_agent': get_finance_agent(debug_mode=True)
                }
                print(f"✅ Статические агенты созданы: {len(self._static_agents_cache)}")
            except Exception as e:
                print(f"⚠️ Ошибка создания статических агентов: {e}")
                self._static_agents_cache = {}
        
        return list(self._static_agents_cache.values())
    
    def _get_dynamic_agents_batch(self) -> List:
        """Получает динамических агентов ОДНИМ батчевым запросом"""
        agents = []
        try:
            with SessionLocal() as session:
                # ОДИН запрос вместо N запросов
                query = text("""
                    SELECT agent_id, name, description, instructions,
                           model_config, tools_config, settings
                    FROM dynamic_agents 
                    WHERE is_active = true 
                    ORDER BY name
                    LIMIT 50
                """)
                result = session.execute(query)
                rows = result.fetchall()
                
                if not rows:
                    return []
                
                print(f"🔄 Создание {len(rows)} динамических агентов батчем...")
                
                # Создаем агентов батчем
                for row in rows:
                    try:
                        agent = DynamicAgentFactory.create_agent_from_db(
                            agent_id=row.agent_id,
                            user_id="playground_user",
                            session_id=f"playground_{row.agent_id}"
                        )
                        if agent:
                            agent.debug_mode = True
                            agents.append(agent)
                    except Exception as e:
                        print(f"⚠️ Ошибка создания агента {row.name}: {e}")
                        continue
                
                print(f"✅ Создано динамических агентов: {len(agents)}")
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки динамических агентов: {e}")
        
        return agents
    
    def get_all_agents(self) -> List:
        """Получает всех агентов оптимизированным способом"""
        static_agents = self._get_static_agents()  # Кэшированные
        dynamic_agents = self._get_dynamic_agents_batch()  # Батчевый запрос
        
        all_agents = static_agents + dynamic_agents
        print(f"🎯 Всего агентов для playground: {len(all_agents)}")
        return all_agents
    
    def get_playground_instance(self) -> Optional[Playground]:
        """Получает экземпляр playground с оптимизированным кэшированием и обработкой ошибок"""
        current_time = time.time()
        
        # Проверяем нужно ли обновление
        if (self._playground_instance and 
            (current_time - self._last_update) < self._cache_ttl):
            return self._playground_instance
        
        # Создаем новый playground с обработкой ошибок
        try:
            print("🔄 Обновление playground...")
            agents = self.get_all_agents()
            
            if agents:
                self._playground_instance = Playground(agents=agents)
                self._last_update = current_time
                print(f"✅ Playground обновлен с {len(agents)} агентами")
                return self._playground_instance
            else:
                print("❌ Не удалось загрузить агентов для playground")
                return None
                
        except Exception as e:
            print(f"❌ Критическая ошибка при создании playground: {e}")
            # Возвращаем старый instance если есть
            if self._playground_instance:
                print("🔄 Возвращаем предыдущий экземпляр playground")
                return self._playground_instance
            return None
    
    def refresh_playground(self) -> bool:
        """Принудительно обновляет playground"""
        print("🔄 Принудительное обновление playground...")
        self._last_update = 0  # Сбрасываем время для принудительного обновления
        
        # Обновляем через кэш менеджер
        cache_manager.refresh_playground()
        
        # Пересоздаем playground
        playground = self.get_playground_instance()
        return playground is not None
    
    def refresh_static_agent(self, agent_id: str) -> bool:
        """Обновляет конкретного статического агента"""
        if agent_id in self._static_agents_cache:
            print(f"🔄 Обновление статического агента: {agent_id}")
            del self._static_agents_cache[agent_id]
            self._last_update = 0  # Принудительное обновление playground
            return True
        return False
    
    def clear_cache(self):
        """Очищает весь кэш для отладки"""
        print("🧹 Очистка кэша playground...")
        self._static_agents_cache.clear()
        self._playground_instance = None
        self._last_update = 0


# Глобальный оптимизированный менеджер
playground_manager = OptimizedPlaygroundManager()

######################################################
## Оптимизированные функции (обратная совместимость)
######################################################

def get_all_agents():
    """Обратная совместимость - использует оптимизированный менеджер"""
    return playground_manager.get_all_agents()

def get_playground_instance():
    """Обратная совместимость - использует оптимизированный менеджер"""
    return playground_manager.get_playground_instance()

def refresh_playground_cache():
    """Обратная совместимость - использует оптимизированный менеджер"""
    return playground_manager.refresh_playground()

######################################################
## АГНО-совместимый Playground Router 
######################################################

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# Создаем статический роутер (стандартный подход Agno)
def create_playground_router():
    """Создает playground router используя стандартный API Agno"""
    current_instance = playground_manager.get_playground_instance()
    if current_instance:
        return current_instance.get_async_router()
    else:
        # Возвращаем пустой роутер если playground недоступен
        return APIRouter()

# Инициализируем роутер при старте (стандартный подход)
playground_router = create_playground_router()

######################################################
## АГНО-совместимый Playground Management Router
######################################################

# Роутер для управления playground (отдельно от нативных endpoints)
playground_management_router = APIRouter(prefix="/playground", tags=["playground-management"])

@playground_management_router.post("/refresh")
async def refresh_playground():
    """Принудительно обновляет playground (АГНО-совместимый)"""
    try:
        success = playground_manager.refresh_playground()
        
        if success:
            return {
                "status": "success", 
                "message": "Playground refreshed successfully (Agno-compatible)",
                "cache_info": {
                    "static_agents_cached": len(playground_manager._static_agents_cache),
                    "last_update": playground_manager._last_update,
                    "agno_compatible": True
                }
            }
        else:
            # Возвращаем информацию о fallback
            return {
                "status": "partial_success",
                "message": "Playground refresh failed, using fallback",
                "cache_info": {
                    "static_agents_cached": len(playground_manager._static_agents_cache),
                    "last_update": playground_manager._last_update,
                    "fallback_used": True
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        # Логируем ошибку но не прерываем работу
        print(f"❌ Ошибка обновления playground: {e}")
        return {
            "status": "error",
            "message": f"Error refreshing playground: {str(e)}",
            "fallback_available": playground_manager._playground_instance is not None
        }

@playground_management_router.post("/refresh/agent/{agent_id}")
async def refresh_single_agent(agent_id: str):
    """Обновляет конкретного агента (АГНО-совместимый)"""
    try:
        # Импортируем DynamicAgentFactory для очистки кэша
        from agents.dynamic.agent_factory import DynamicAgentFactory
        
        # Пробуем обновить статического агента
        if playground_manager.refresh_static_agent(agent_id):
            return {
                "status": "success",
                "message": f"Static agent {agent_id} refreshed (Agno-compatible)",
                "agent_type": "static",
                "agno_compatible": True
            }
        
        # Для динамических агентов обновляем через кэш
        cache_manager.refresh_agent(agent_id)
        
        # КРИТИЧНО: Очищаем кэш DynamicAgentFactory для этого агента
        DynamicAgentFactory.clear_config_cache(agent_id)
        
        # Принудительно обновляем playground для динамических агентов
        playground_manager._last_update = 0  # Принудительное обновление
        playground_manager.get_playground_instance()  # Пересоздаем
        
        return {
            "status": "success", 
            "message": f"Dynamic agent {agent_id} refreshed (Agno-compatible)",
            "agent_type": "dynamic",
            "agno_compatible": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing agent: {str(e)}")

@playground_management_router.get("/stats")
async def playground_stats():
    """Статистика playground для мониторинга производительности"""
    current_router = create_playground_router()
    routes_count = len(current_router.routes) if current_router else 0
    
    return {
        "static_agents_cached": len(playground_manager._static_agents_cache),
        "playground_active": playground_manager._playground_instance is not None,
        "last_update": playground_manager._last_update,
        "cache_ttl": playground_manager._cache_ttl,
        "uptime_seconds": time.time() - playground_manager._last_update if playground_manager._last_update > 0 else 0,
        "routes_count": routes_count,
        "agno_compatible": True
    }
