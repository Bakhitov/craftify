"""
Автоматическое обновление кэша при изменениях.
Упрощенная версия для максимальной производительности.
"""
import time
from typing import Dict, Any
from .cache_manager import cache_manager


class AutoCacheRefresh:
    """
    Автоматическое обновление кэша при операциях с агентами и инструментами.
    Простой и быстрый подход без лишних накладных расходов.
    """
    
    def __init__(self):
        self.last_refresh = time.time()
        self.refresh_count = 0
        self.batch_operations = []
        self.batch_timeout = 1.0  # 1 секунда для батчинга
    
    def refresh_after_agent_operation(self, agent_id: str, operation: str = "update"):
        """Обновляет кэш после операции с агентом"""
        try:
            # Обновляем кэш агента
            cache_manager.refresh_agent(agent_id)
            
            # Очищаем список агентов для пересоздания
            cache_manager.cache.delete("agents:list")
            
            self.refresh_count += 1
            self.last_refresh = time.time()
            
            print(f"✅ Кэш агента {agent_id} обновлен после операции: {operation}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении кэша агента {agent_id}: {e}")
    
    def refresh_after_tool_operation(self, tool_id: str, operation: str = "update"):
        """Обновляет кэш после операции с инструментом"""
        try:
            # Обновляем кэш инструмента
            cache_manager.refresh_tool(tool_id)
            
            self.refresh_count += 1
            self.last_refresh = time.time()
            
            print(f"✅ Кэш инструмента {tool_id} обновлен после операции: {operation}")
            
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении кэша инструмента {tool_id}: {e}")
    
    def batch_refresh(self, operations: list):
        """Батчевое обновление кэша для множественных операций"""
        try:
            start_time = time.time()
            
            # Группируем операции по типу
            agents_to_refresh = set()
            tools_to_refresh = set()
            
            for operation in operations:
                if operation.get("type") == "agent":
                    agents_to_refresh.add(operation.get("id"))
                elif operation.get("type") == "tool":
                    tools_to_refresh.add(operation.get("id"))
            
            # Обновляем агентов
            for agent_id in agents_to_refresh:
                cache_manager.refresh_agent(agent_id)
            
            # Обновляем инструменты
            for tool_id in tools_to_refresh:
                cache_manager.refresh_tool(tool_id)
            
            # Очищаем общие списки
            if agents_to_refresh:
                cache_manager.cache.delete("agents:list")
            
            elapsed = time.time() - start_time
            self.refresh_count += len(operations)
            self.last_refresh = time.time()
            
            print(f"✅ Батчевое обновление кэша: {len(operations)} операций за {elapsed:.3f}с")
            
        except Exception as e:
            print(f"⚠️ Ошибка при батчевом обновлении кэша: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика автообновления"""
        return {
            "last_refresh": self.last_refresh,
            "refresh_count": self.refresh_count,
            "uptime_seconds": time.time() - self.last_refresh if self.last_refresh > 0 else 0,
            "batch_timeout": self.batch_timeout,
            "pending_operations": len(self.batch_operations)
        }


# Глобальный экземпляр автообновления
auto_cache = AutoCacheRefresh()
