"""
API маршруты для управления кэшем и получения статистики.
Демонстрирует работу автообновления кэша.
"""
from fastapi import APIRouter
from typing import Dict, Any

from agents.cache.cache_manager import cache_manager
from agents.cache.auto_refresh import auto_cache
from agents.selector import refresh_agent_cache

######################################################
## Routes for Cache Management & Stats
######################################################

cache_router = APIRouter(prefix="/cache", tags=["Cache"])

@cache_router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Получение детальной статистики кэша.
    
    Returns:
        Dict: Статистика работы кэша и автообновления
    """
    try:
        # Получаем статистику от cache_manager
        cache_stats = cache_manager.stats()
        
        # Получаем статистику автообновления
        auto_refresh_stats = auto_cache.get_stats()
        
        # Проверяем здоровье кэша
        health_check = cache_manager.health_check()
        
        return {
            "cache_manager": cache_stats,
            "auto_refresh": auto_refresh_stats,
            "health": health_check,
            "auto_refresh_enabled": True,
            "description": "Кэш обновляется автоматически при CRUD операциях с агентами и инструментами"
        }
        
    except Exception as e:
        return {
            "error": f"Ошибка получения статистики кэша: {e}",
            "cache_manager": {},
            "auto_refresh": {},
            "health": {"status": "unhealthy"}
        }

@cache_router.post("/refresh")
async def manual_refresh_cache():
    """
    Ручное обновление всего кэша.
    
    Returns:
        Dict: Результат операции обновления
    """
    try:
        # Обновляем весь кэш через cache_manager
        success = cache_manager.refresh_all()
        
        # Обновляем также через агентский registry
        refresh_agent_cache()
        
        if success:
            return {
                "status": "success",
                "message": "Кэш успешно обновлен",
                "auto_refresh_active": True,
                "note": "Кэш также обновляется автоматически при изменениях"
            }
        else:
            return {
                "status": "partial_success",
                "message": "Кэш частично обновлен",
                "note": "Некоторые операции могли завершиться с ошибками"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка обновления кэша: {e}"
        }

@cache_router.post("/refresh/agent/{agent_id}")
async def refresh_specific_agent_cache(agent_id: str):
    """
    Ручное обновление кэша конкретного агента.
    
    Args:
        agent_id: ID агента для обновления кэша
        
    Returns:
        Dict: Результат операции
    """
    try:
        # Обновляем кэш конкретного агента
        success = cache_manager.refresh_agent(agent_id)
        
        # Также обновляем через registry
        refresh_agent_cache(agent_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Кэш агента {agent_id} обновлен",
                "agent_id": agent_id,
                "auto_refresh_note": "Кэш также обновляется автоматически при изменениях агента"
            }
        else:
            return {
                "status": "error",
                "message": f"Ошибка обновления кэша агента {agent_id}",
                "agent_id": agent_id
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка: {e}",
            "agent_id": agent_id
        }

@cache_router.post("/cleanup")
async def cleanup_expired_cache():
    """
    Очистка истекших элементов кэша.
    
    Returns:
        Dict: Количество очищенных элементов
    """
    try:
        cleaned_count = cache_manager.cleanup()
        
        return {
            "status": "success",
            "message": f"Очищено {cleaned_count} истекших элементов",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка очистки кэша: {e}",
            "cleaned_count": 0
        }

@cache_router.get("/health")
async def cache_health_check():
    """
    Проверка здоровья системы кэширования.
    
    Returns:
        Dict: Состояние системы кэша
    """
    try:
        health = cache_manager.health_check()
        auto_stats = auto_cache.get_stats()
        
        return {
            "cache_health": health,
            "auto_refresh": {
                "enabled": True,
                "last_refresh": auto_stats.get("last_refresh", 0),
                "total_refreshes": auto_stats.get("refresh_count", 0)
            },
            "system_status": "operational" if health.get("status") == "healthy" else "degraded"
        }
        
    except Exception as e:
        return {
            "cache_health": {"status": "unhealthy", "error": str(e)},
            "auto_refresh": {"enabled": False, "error": str(e)},
            "system_status": "error"
        }

@cache_router.get("/demo")
async def cache_demo_info():
    """
    Информация о системе автообновления кэша для демонстрации.
    
    Returns:
        Dict: Описание работы автообновления
    """
    return {
        "title": "Система автообновления кэша",
        "description": "Кэш агентов и инструментов обновляется автоматически",
        "features": [
            "Автообновление при создании агентов/инструментов",
            "Автообновление при изменении агентов/инструментов", 
            "Автообновление при удалении агентов/инструментов",
            "Event-driven архитектура с CacheEventBus",
            "Батчевые операции для производительности",
            "Автоматическая очистка истекших элементов"
        ],
        "components": {
            "cache_manager": "Основной менеджер кэша",
            "auto_cache": "Система автообновления",
            "event_bus": "Шина событий для уведомлений",
            "simple_cache": "Быстрое хранилище в памяти"
        },
        "automatic_triggers": [
            "POST /dynamic-agents - создание агента",
            "PUT /dynamic-agents/{id} - обновление агента",
            "DELETE /dynamic-agents/{id} - удаление агента",
            "POST /dynamic-agents/{id}/activate - активация агента",
            "POST /dynamic-tools - создание инструмента", 
            "PUT /dynamic-tools/{id} - обновление инструмента",
            "DELETE /dynamic-tools/{id} - удаление инструмента"
        ]
    } 