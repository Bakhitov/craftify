"""
Типизированные исключения для Agent API Platform.
Обеспечивают детальную диагностику и упрощают отладку.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AgentAPIError(Exception):
    """Базовое исключение для Agent API Platform"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __str__(self):
        base_msg = self.message
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base_msg += f" (details: {details_str})"
        if self.cause:
            base_msg += f" (caused by: {self.cause})"
        return base_msg


class AgentNotFoundError(AgentAPIError):
    """Агент не найден"""
    
    def __init__(self, agent_id: str, agent_type: Optional[str] = None):
        details = {"agent_id": agent_id}
        if agent_type:
            details["agent_type"] = agent_type
        super().__init__(f"Agent '{agent_id}' not found", details)


class AgentCreationError(AgentAPIError):
    """Ошибка создания агента"""
    
    def __init__(self, agent_id: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Failed to create agent '{agent_id}': {reason}",
            {"agent_id": agent_id, "reason": reason},
            cause
        )


class ToolNotFoundError(AgentAPIError):
    """Инструмент не найден"""
    
    def __init__(self, tool_id: str, tool_type: Optional[str] = None):
        details = {"tool_id": tool_id}
        if tool_type:
            details["tool_type"] = tool_type
        super().__init__(f"Tool '{tool_id}' not found", details)


class DatabaseError(AgentAPIError):
    """Ошибка базы данных"""
    
    def __init__(self, operation: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Database operation failed: {operation}",
            {"operation": operation},
            cause
        )


class ConfigurationError(AgentAPIError):
    """Ошибка конфигурации"""
    
    def __init__(self, config_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Configuration error in {config_type}: {reason}",
            {"config_type": config_type, "reason": reason, **(details or {})}
        )


class ValidationError(AgentAPIError):
    """Ошибка валидации данных"""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            {"field": field, "value": str(value), "reason": reason}
        )


def handle_agent_error(operation: str, agent_id: str, error: Exception, 
                      context: Optional[Dict[str, Any]] = None) -> AgentAPIError:
    """
    Единая точка обработки ошибок агентов.
    Конвертирует общие исключения в типизированные AgentAPIError.
    
    Args:
        operation: Название операции (create, get, update, etc.)
        agent_id: ID агента
        error: Исходное исключение
        context: Дополнительный контекст
        
    Returns:
        Типизированное исключение AgentAPIError
    """
    context = context or {}
    
    # Логируем с полным stack trace
    logger.error(
        f"Agent operation failed: {operation} for agent '{agent_id}'",
        extra={"agent_id": agent_id, "operation": operation, **context},
        exc_info=True
    )
    
    # Конвертируем в типизированное исключение
    if isinstance(error, AgentAPIError):
        return error
    elif "not found" in str(error).lower():
        return AgentNotFoundError(agent_id)
    elif "database" in str(error).lower() or "connection" in str(error).lower():
        return DatabaseError(f"{operation} agent {agent_id}", error)
    else:
        return AgentCreationError(agent_id, str(error), error)


def handle_tool_error(operation: str, tool_id: str, error: Exception,
                     context: Optional[Dict[str, Any]] = None) -> AgentAPIError:
    """
    Единая точка обработки ошибок инструментов.
    
    Args:
        operation: Название операции
        tool_id: ID инструмента
        error: Исходное исключение
        context: Дополнительный контекст
        
    Returns:
        Типизированное исключение AgentAPIError
    """
    context = context or {}
    
    logger.error(
        f"Tool operation failed: {operation} for tool '{tool_id}'",
        extra={"tool_id": tool_id, "operation": operation, **context},
        exc_info=True
    )
    
    if isinstance(error, AgentAPIError):
        return error
    elif "not found" in str(error).lower():
        return ToolNotFoundError(tool_id)
    else:
        return AgentAPIError(f"Tool {operation} failed for '{tool_id}': {str(error)}", 
                           {"tool_id": tool_id, "operation": operation}, error)


def safe_execute(operation: str, func, *args, **kwargs) -> Any:
    """
    Безопасное выполнение операции с автоматической обработкой ошибок.
    
    Args:
        operation: Название операции для логирования
        func: Функция для выполнения
        *args, **kwargs: Аргументы функции
        
    Returns:
        Результат выполнения функции
        
    Raises:
        AgentAPIError: При любой ошибке
    """
    try:
        return func(*args, **kwargs)
    except AgentAPIError:
        raise  # Перебрасываем типизированные исключения как есть
    except Exception as e:
        logger.error(f"Operation '{operation}' failed", exc_info=True)
        raise AgentAPIError(f"Operation '{operation}' failed: {str(e)}", 
                          {"operation": operation}, e)
