"""
Единая точка доступа к агентам - делегирует все операции в agent_registry.
Принципы: DRY (Don't Repeat Yourself), единая ответственность, простота.
"""
from typing import List, Optional
from agno.agent import Agent
from agents.registry.agent_registry import agent_registry

# === ЕДИНАЯ ТОЧКА ДОСТУПА - ВСЕ ЧЕРЕЗ REGISTRY ===

def get_available_agents() -> List[str]:
    """Возвращает список всех доступных агентов"""
    return agent_registry.get_available_agents()


def get_agent(
    agent_id: str,
    model_id: str = "gpt-4.1", 
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Получает агента по ID (статического или динамического)"""
    return agent_registry.get_agent(
        agent_id=agent_id,
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )


def get_static_agents() -> List[str]:
    """Возвращает список статических агентов"""
    return agent_registry.get_static_agents()


def get_dynamic_agents() -> List[str]:
    """Возвращает список динамических агентов"""
    return agent_registry.get_dynamic_agents()


def is_static_agent(agent_id: str) -> bool:
    """Проверяет является ли агент статическим"""
    return agent_registry.is_static_agent(agent_id)


def is_dynamic_agent(agent_id: str) -> bool:
    """Проверяет является ли агент динамическим"""
    return agent_registry.is_dynamic_agent(agent_id)


def get_agent_info(agent_id: str) -> dict:
    """Получает информацию об агенте"""
    return agent_registry.get_agent_info(agent_id)


def get_static_agent_details(agent_id: str) -> dict:
    """Получает детальную информацию о статическом агенте"""
    return agent_registry.get_static_agent_details(agent_id)


def refresh_agent_cache(agent_id: Optional[str] = None):
    """Обновляет кэш агентов"""
    return agent_registry.refresh_cache(agent_id)


def get_static_agent_basic_info(agent_id: str) -> dict:
    """Быстрое получение базовой информации о статическом агенте"""
    return agent_registry.get_static_agent_basic_info(agent_id)
