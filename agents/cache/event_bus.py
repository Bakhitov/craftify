"""
Упрощенная система событий для кэша.
Минимальные накладные расходы, максимальная производительность.
"""
from typing import Dict, List, Callable, Any
import time


class EventType:
    """Типы событий кэша"""
    AGENT_UPDATED = "agent_updated"
    TOOL_UPDATED = "tool_updated"
    CACHE_CLEARED = "cache_cleared"


class CacheEventBus:
    """
    Упрощенная система событий для кэша.
    Быстрая, без лишних накладных расходов.
    """
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._stats = {
            "events_emitted": 0,
            "listeners_count": 0,
            "errors": 0
        }
    
    def on(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Быстрая регистрация обработчика события"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        self._listeners[event_type].append(callback)
        self._stats["listeners_count"] += 1
    
    def emit(self, event_type: str, data: Dict[str, Any]):
        """Быстрое уведомление о событии"""
        try:
            if event_type in self._listeners:
                for callback in self._listeners[event_type]:
                    try:
                        callback(data)
                    except Exception as e:
                        self._stats["errors"] += 1
                        print(f"⚠️ Ошибка в обработчике события {event_type}: {e}")
            
            self._stats["events_emitted"] += 1
            
        except Exception as e:
            self._stats["errors"] += 1
            print(f"⚠️ Ошибка при отправке события {event_type}: {e}")
    
    def get_listener_count(self) -> int:
        """Количество активных обработчиков"""
        return sum(len(listeners) for listeners in self._listeners.values())
    
    def stats(self) -> Dict[str, Any]:
        """Быстрая статистика событий"""
        return {
            "events_emitted": self._stats["events_emitted"],
            "total_listeners": self._stats["listeners_count"],
            "active_listeners": self.get_listener_count(),
            "errors": self._stats["errors"],
            "event_types": list(self._listeners.keys())
        } 