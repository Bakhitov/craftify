"""
Кастомные исключения для Agent API Platform.
Обеспечивают типизированную обработку ошибок.
"""

from enum import Enum
from typing import Optional, Dict, Any

class ErrorType(Enum):
    """Типы ошибок в системе агентов"""
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_CREATION_FAILED = "agent_creation_failed" 
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    TOOL_IMPORT_ERROR = "tool_import_error"
    MEMORY_ERROR = "memory_error"
    STORAGE_ERROR = "storage_error"
    VALIDATION_ERROR = "validation_error"
    AUDIO_ARTIFACT_ERROR = "audio_artifact_error"
    COMPATIBILITY_ERROR = "compatibility_error"

class AgentAPIError(Exception):
    """Базовый класс для всех ошибок Agent API"""
    def __init__(self, error_type: ErrorType, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message 
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует ошибку в словарь для API ответов"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details
        }

class AgentNotFoundError(AgentAPIError):
    """Агент не найден"""
    def __init__(self, agent_id: str, available_agents: Optional[list] = None):
        super().__init__(
            ErrorType.AGENT_NOT_FOUND,
            f"Agent '{agent_id}' not found",
            {"agent_id": agent_id, "available_agents": available_agents}
        )

class AgentCreationError(AgentAPIError):
    """Ошибка создания агента"""
    def __init__(self, agent_id: str, reason: str, agent_type: str = "unknown"):
        super().__init__(
            ErrorType.AGENT_CREATION_FAILED,
            f"Failed to create {agent_type} agent '{agent_id}': {reason}",
            {"agent_id": agent_id, "agent_type": agent_type, "reason": reason}
        )

class DatabaseError(AgentAPIError):
    """Ошибка базы данных"""
    def __init__(self, operation: str, details: str):
        super().__init__(
            ErrorType.DATABASE_ERROR,
            f"Database error during {operation}: {details}",
            {"operation": operation}
        )

class AudioArtifactError(AgentAPIError):
    """Ошибка с аудио артефактами"""
    def __init__(self, session_id: str, artifact_id: str, reason: str):
        super().__init__(
            ErrorType.AUDIO_ARTIFACT_ERROR,
            f"Invalid audio artifact in session {session_id}: {reason}",
            {"session_id": session_id, "artifact_id": artifact_id, "reason": reason}
        )
