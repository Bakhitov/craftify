"""
Упрощенный менеджер кэша - быстрый и легковесный.
Принципы: минимум кода, максимум производительности, простота понимания.
"""
import time
from typing import Optional, Dict, Any, List
from agno.agent import Agent

from .simple_cache import SimpleCache
from .event_bus import CacheEventBus, EventType as CacheEventType


class CacheManager:
    """
    Упрощенный менеджер кэша для максимальной производительности.
    - Простой fallback на agno при ошибках
    - Минимум накладных расходов
    - Быстрые операции
    """
    
    def __init__(self):
        self.cache = SimpleCache()
        self.event_bus = CacheEventBus()
        self._setup_event_handlers()
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "refreshes": 0,
            "errors": 0
        }
    
    def _setup_event_handlers(self):
        """Настройка обработчиков событий кэша"""
        def clear_agents(data: Dict[str, Any]):
            # Очищаем кэш агентов при изменении
            pattern = f"agent:*"
            keys = self.cache.get_keys_by_pattern(pattern)
            for key in keys:
                self.cache.delete(key)
            print(f"🧹 Очищен кэш агентов: {len(keys)} ключей")

        def clear_tools(data: Dict[str, Any]):
            # Очищаем кэш инструментов при изменении  
            pattern = f"tool:*"
            keys = self.cache.get_keys_by_pattern(pattern)
            for key in keys:
                self.cache.delete(key)
            print(f"🧹 Очищен кэш инструментов: {len(keys)} ключей")

        # Подписываемся на события
        self.event_bus.on(CacheEventType.AGENT_UPDATED, clear_agents)
        self.event_bus.on(CacheEventType.TOOL_UPDATED, clear_tools)
    
    # === ОСНОВНЫЕ МЕТОДЫ КЭША ===
    
    def get_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """Быстрое получение агента из кэша"""
        try:
            cache_key = f"agent:{agent_id}"
            agent = self.cache.get(cache_key)
            
            if agent:
                self._stats["cache_hits"] += 1
                return agent
            else:
                self._stats["cache_misses"] += 1
                return None  # Fallback на agno
                
        except Exception:
            self._stats["errors"] += 1
            return None  # Fallback на agno
    
    def set_agent(self, agent_id: str, agent: Agent, ttl: int = 600) -> bool:
        """Быстрое сохранение агента в кэш"""
        try:
            cache_key = f"agent:{agent_id}"
            return self.cache.set(cache_key, agent, ttl=ttl)
        except Exception:
            self._stats["errors"] += 1
            return False
    
    def get_agents_list(self) -> Optional[List[str]]:
        """Получение списка агентов из кэша"""
        try:
            agents_list = self.cache.get("agents:list")
            if agents_list:
                self._stats["cache_hits"] += 1
                return agents_list
            else:
                self._stats["cache_misses"] += 1
                return None
        except Exception:
            self._stats["errors"] += 1
            return None
    
    def set_agents_list(self, agents_list: List[str], ttl: int = 300) -> bool:
        """Сохранение списка агентов в кэш"""
        try:
            return self.cache.set("agents:list", agents_list, ttl=ttl)
        except Exception:
            self._stats["errors"] += 1
            return False
    
    # === МЕТОДЫ ОБНОВЛЕНИЯ ===
    
    def refresh_agent(self, agent_id: str) -> bool:
        """Обновление конкретного агента"""
        try:
            self.event_bus.emit(CacheEventType.AGENT_UPDATED, {
                "agent_id": agent_id,
                "timestamp": time.time()
            })
            return True
        except Exception:
            self._stats["errors"] += 1
            return False
    
    def refresh_tool(self, tool_id: str) -> bool:
        """Обновление конкретного инструмента"""
        try:
            self.event_bus.emit(CacheEventType.TOOL_UPDATED, {
                "tool_id": tool_id,
                "timestamp": time.time()
            })
            return True
        except Exception:
            self._stats["errors"] += 1
            return False
    
    def refresh_all(self) -> bool:
        """Полная очистка кэша"""
        try:
            self.event_bus.emit(CacheEventType.CACHE_CLEARED, {
                "timestamp": time.time()
            })
            return True
        except Exception:
            self._stats["errors"] += 1
            return False
    
    # === СЛУЖЕБНЫЕ МЕТОДЫ ===
    
    def cleanup(self) -> int:
        """Очистка истекших элементов"""
        try:
            return self.cache.cleanup()
        except Exception:
            self._stats["errors"] += 1
            return 0
    
    def stats(self) -> Dict[str, Any]:
        """Быстрая статистика кэша"""
        try:
            cache_stats = self.cache.get_stats()
            event_stats = self.event_bus.stats()
            
            return {
                "cache": cache_stats,
                "events": event_stats,
                "operations": self._stats,
                "cache_keys": {
                    "total": cache_stats["total_keys"],
                    "active": cache_stats["active_keys"],
                    "expired": cache_stats["expired_keys"]
                }
            }
        except Exception:
            self._stats["errors"] += 1
            return {"error": "Failed to get stats"}
    
    def health_check(self) -> Dict[str, Any]:
        """Быстрая проверка здоровья кэша"""
        try:
            cache_stats = self.cache.get_stats()
            error_rate = self._stats["errors"] / max(1, sum(self._stats.values()))
            
            is_healthy = (
                cache_stats["total_keys"] < 10000 and  # Не переполнен
                error_rate < 0.1 and  # Мало ошибок
                self.event_bus.get_listener_count() > 0  # События работают
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "cache_size": cache_stats["total_keys"],
                "error_rate": round(error_rate, 3),
                "event_listeners": self.event_bus.get_listener_count(),
                "issues": [] if is_healthy else ["High cache size or error rate"]
            }
        except Exception:
            return {
                "status": "unhealthy",
                "error": "Health check failed"
            }


# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager() 