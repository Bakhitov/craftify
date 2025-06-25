"""
Простая система событий для уведомления об изменениях.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Типы событий в системе"""
    AGENT_CREATED = "agent_created"
    AGENT_UPDATED = "agent_updated"
    AGENT_DELETED = "agent_deleted"
    TOOL_CREATED = "tool_created"
    TOOL_UPDATED = "tool_updated"
    TOOL_DELETED = "tool_deleted"
    PLAYGROUND_REFRESH = "playground_refresh"
    PLAYGROUND_UPDATED = "playground_updated"
    CACHE_CLEAR = "cache_clear"
    CACHE_CLEARED = "cache_cleared"


# Алиас для совместимости с cache_manager
CacheEventType = EventType


class EventBus:
    """
    Простая система событий для внутренних уведомлений.
    Синхронная обработка событий.
    """
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._event_count = 0
    
    def emit(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """
        Отправляет событие всем подписчикам.
        
        Args:
            event_type: Тип события
            data: Данные события
        """
        if data is None:
            data = {}
        
        self._event_count += 1
        
        logger.debug(f"Emitting event: {event_type} with data: {data}")
        
        # Вызываем всех слушателей для этого типа события
        for callback in self._listeners[event_type]:
            try:
                callback(data)
                logger.debug(f"Event handler executed successfully for {event_type}")
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
                # Продолжаем выполнение других обработчиков
    
    def on(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Подписывается на событие.
        
        Args:
            event_type: Тип события для подписки
            callback: Функция-обработчик события
        """
        self._listeners[event_type].append(callback)
        logger.debug(f"Added listener for event: {event_type}")
    
    def off(self, event_type: str, callback: Callable = None) -> None:
        """
        Отписывается от события.
        
        Args:
            event_type: Тип события
            callback: Конкретный обработчик (если None, удаляются все)
        """
        if callback is None:
            # Удаляем всех слушателей для этого типа
            self._listeners[event_type].clear()
            logger.debug(f"Removed all listeners for event: {event_type}")
        else:
            # Удаляем конкретный обработчик
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Removed specific listener for event: {event_type}")
    
    def has_listeners(self, event_type: str) -> bool:
        """
        Проверяет есть ли слушатели для события.
        
        Args:
            event_type: Тип события
            
        Returns:
            True если есть слушатели
        """
        return len(self._listeners[event_type]) > 0
    
    def get_listener_count(self, event_type: str = None) -> int:
        """
        Возвращает количество слушателей.
        
        Args:
            event_type: Тип события (если None, возвращает общее количество)
            
        Returns:
            Количество слушателей
        """
        if event_type:
            return len(self._listeners[event_type])
        
        return sum(len(listeners) for listeners in self._listeners.values())
    
    def stats(self) -> Dict[str, Any]:
        """Возвращает статистику событий"""
        return {
            "total_events_emitted": self._event_count,
            "event_types": list(self._listeners.keys()),
            "listeners_per_event": {
                event_type: len(listeners) 
                for event_type, listeners in self._listeners.items()
            },
            "total_listeners": self.get_listener_count()
        }
    
    def clear(self) -> None:
        """Очищает всех слушателей"""
        self._listeners.clear()
        logger.debug("Cleared all event listeners")
    
    # Алиасы для совместимости с cache_manager
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Алиас для метода on()"""
        self.on(event_type, callback)
    
    def publish(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Алиас для метода emit()"""
        self.emit(event_type, data) 