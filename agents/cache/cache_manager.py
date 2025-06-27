"""
Простой TTL-кэш для агентов.
Принципы: простота, надежность, минимум кода.
"""
import time
from typing import Optional, Dict, Any, List
from agno.agent import Agent


class SimpleCacheManager:
    """
    Простой TTL-кэш для агентов.
    Без сложных событий - просто быстрый кэш с TTL.
    """
    
    def __init__(self, default_ttl: int = 600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "cache_deletes": 0,
            "cleanup_runs": 0
        }
    
    def get_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """Получение агента из кэша"""
        try:
            cache_key = f"agent:{agent_id}"
            
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                # Проверяем TTL
                if time.time() < entry['expires_at']:
                    self._stats["cache_hits"] += 1
                    return entry['value']
                else:
                    # Истек TTL - удаляем
                    del self.cache[cache_key]
            
            self._stats["cache_misses"] += 1
            return None
                
        except Exception:
            self._stats["cache_misses"] += 1
            return None
    
    def set_agent(self, agent_id: str, agent: Agent, ttl: Optional[int] = None) -> bool:
        """Сохранение агента в кэш"""
        try:
            cache_key = f"agent:{agent_id}"
            expires_at = time.time() + (ttl or self.default_ttl)
            
            self.cache[cache_key] = {
                'value': agent,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            self._stats["cache_sets"] += 1
            return True
            
        except Exception:
            return False
    
    def get_agents_list(self) -> Optional[List[str]]:
        """Получение списка агентов из кэша"""
        try:
            return self.get("agents:list")
        except Exception:
            return None
    
    def set_agents_list(self, agents_list: List[str], ttl: Optional[int] = None) -> bool:
        """Сохранение списка агентов в кэш"""
        try:
            return self.set("agents:list", agents_list, ttl)
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Универсальное получение из кэша"""
        try:
            if key in self.cache:
                entry = self.cache[key]
                
                if time.time() < entry['expires_at']:
                    self._stats["cache_hits"] += 1
                    return entry['value']
                else:
                    del self.cache[key]
            
            self._stats["cache_misses"] += 1
            return None
            
        except Exception:
            self._stats["cache_misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Универсальное сохранение в кэш"""
        try:
            expires_at = time.time() + (ttl or self.default_ttl)
            
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            self._stats["cache_sets"] += 1
            return True
            
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Удаление из кэша"""
        try:
            if key in self.cache:
                del self.cache[key]
                self._stats["cache_deletes"] += 1
                return True
            return False
        except Exception:
            return False
    
    def clear(self) -> bool:
        """Полная очистка кэша"""
        try:
            self.cache.clear()
            return True
        except Exception:
            return False
    
    def cleanup(self) -> int:
        """Очистка истекших элементов"""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items() 
                if current_time >= entry['expires_at']
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            self._stats["cleanup_runs"] += 1
            return len(expired_keys)
            
        except Exception:
            return 0
    
    def refresh_agent(self, agent_id: str) -> bool:
        """Обновление агента - просто удаляем из кэша"""
        return self.delete(f"agent:{agent_id}")
    
    def refresh_all(self) -> bool:
        """Полное обновление - очищаем весь кэш"""
        return self.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Статистика кэша"""
        try:
            total_keys = len(self.cache)
            current_time = time.time()
            
            active_keys = sum(
                1 for entry in self.cache.values() 
                if current_time < entry['expires_at']
            )
            expired_keys = total_keys - active_keys
            
            hit_rate = 0.0
            total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
            if total_requests > 0:
                hit_rate = self._stats["cache_hits"] / total_requests
            
            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "expired_keys": expired_keys,
                "hit_rate": round(hit_rate, 3),
                "operations": self._stats.copy()
            }
        except Exception:
            return {"error": "Failed to get stats"}
    
    def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья кэша"""
        try:
            stats = self.stats()
            
            is_healthy = (
                stats["total_keys"] < 10000 and  # Не переполнен
                stats["hit_rate"] > 0.1  # Есть попадания
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "cache_size": stats["total_keys"],
                "hit_rate": stats["hit_rate"],
                "issues": [] if is_healthy else ["High cache size or low hit rate"]
            }
        except Exception:
            return {
                "status": "unhealthy",
                "error": "Health check failed"
            }


# Глобальный экземпляр кэш-менеджера
cache_manager = SimpleCacheManager() 