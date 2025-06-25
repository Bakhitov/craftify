"""
Простая система кэширования для агентов и компонентов.
Минимальная реализация с событийным обновлением.
"""

from .simple_cache import SimpleCache
from .event_bus import EventBus
from .cache_manager import CacheManager

# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager()

__all__ = [
    "SimpleCache",
    "EventBus", 
    "CacheManager",
    "cache_manager"
] 