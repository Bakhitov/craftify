"""
Упрощенные API эндпоинты для управления кэшем.
Принципы: быстро, просто, минимум кода.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from agents.cache import cache_manager

logger = logging.getLogger(__name__)

cache_router = APIRouter(prefix="/cache", tags=["Cache Management"])


@cache_router.post("/refresh/agent/{agent_id}")
async def refresh_agent(agent_id: str) -> Dict[str, Any]:
    """Быстро обновляет кэш конкретного агента"""
    success = cache_manager.refresh_agent(agent_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Agent {agent_id} cache refreshed",
            "agent_id": agent_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh agent {agent_id}"
        )


@cache_router.post("/refresh/tool/{tool_id}")
async def refresh_tool(tool_id: str) -> Dict[str, Any]:
    """Быстро обновляет кэш конкретного инструмента"""
    success = cache_manager.refresh_tool(tool_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Tool {tool_id} cache refreshed",
            "tool_id": tool_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tool {tool_id}"
        )


@cache_router.post("/refresh/playground")
async def refresh_playground() -> Dict[str, Any]:
    """Быстро обновляет кэш playground"""
    success = cache_manager.refresh_playground()
    
    if success:
        return {
            "status": "success",
            "message": "Playground cache refreshed"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh playground"
        )


@cache_router.post("/refresh/all")
async def refresh_all() -> Dict[str, Any]:
    """Быстро очищает весь кэш"""
    success = cache_manager.refresh_all()
    
    if success:
        return {
            "status": "success",
            "message": "All cache cleared and refreshed"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@cache_router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Быстрая статистика кэша"""
    stats = cache_manager.stats()
    return {
        "status": "success",
        "data": stats
    }


@cache_router.post("/cleanup")
async def cleanup_cache() -> Dict[str, Any]:
    """Быстро очищает истекшие элементы кэша"""
    expired_count = cache_manager.cleanup()
    return {
        "status": "success",
        "message": f"Cleaned up {expired_count} expired entries",
        "expired_count": expired_count
    }


@cache_router.get("/health")
async def cache_health() -> Dict[str, Any]:
    """Быстрая проверка состояния системы кэширования"""
    health_info = cache_manager.health_check()
    
    if health_info["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_info
        )
    
    return {
        "status": "success",
        "data": health_info
    } 