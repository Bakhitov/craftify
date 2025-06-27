"""
V1 API Router - основной роутер для всех v1 endpoints.
"""

from fastapi import APIRouter
from .agents import agents_router
from .dynamic_agents import dynamic_agents_router
from .dynamic_tools import router as dynamic_tools_router
from .health import health_router
from .mcp_tools import router as mcp_tools_router
from .agno_base import agno_base_router
from .cache_stats import cache_router

# Создаем основной v1 роутер
v1_router = APIRouter(prefix="/v1")

# Подключаем все роутеры
v1_router.include_router(health_router)
v1_router.include_router(agents_router)
v1_router.include_router(dynamic_agents_router)
v1_router.include_router(dynamic_tools_router)
v1_router.include_router(mcp_tools_router)
v1_router.include_router(agno_base_router)
v1_router.include_router(cache_router)
