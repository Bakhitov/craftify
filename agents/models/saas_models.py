"""
Pydantic модели для SaaS архитектуры с поддержкой мультитенантности.
Обеспечивают изоляцию между тенантами и безопасность платформы.
"""

from typing import Dict, Any, List, Optional, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

# Импорт типизированных моделей инструментов
from agents.models import StaticToolConfig, DynamicToolConfig, MCPToolConfig


class SubscriptionTier(str, Enum):
    """Уровни подписки для SaaS"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantConfig(BaseModel):
    """Конфигурация тенанта"""
    tenant_id: str = Field(..., description="Уникальный ID тенанта")
    name: str = Field(..., description="Название организации")
    subscription_tier: SubscriptionTier = Field(default=SubscriptionTier.FREE)
    
    # Лимиты по подписке
    max_agents: int = Field(default=5, description="Максимальное количество агентов")
    max_tools: int = Field(default=10, description="Максимальное количество инструментов")
    max_concurrent_runs: int = Field(default=3, description="Максимальное количество одновременных запусков")
    max_tool_calls_per_minute: int = Field(default=100, description="Лимит вызовов инструментов в минуту")
    
    # Возможности по подписке
    can_create_custom_agents: bool = Field(default=True)
    can_create_custom_tools: bool = Field(default=False)
    can_use_advanced_models: bool = Field(default=False)
    can_access_api: bool = Field(default=True)
    
    # Настройки безопасности
    sandbox_enabled: bool = Field(default=True, description="Включить sandbox для пользовательского кода")
    code_validation_strict: bool = Field(default=True, description="Строгая валидация кода")
    
    @validator('max_agents')
    def validate_agent_limits(cls, v, values):
        tier = values.get('subscription_tier')
        limits = {
            SubscriptionTier.FREE: 5,
            SubscriptionTier.BASIC: 20,
            SubscriptionTier.PRO: 100,
            SubscriptionTier.ENTERPRISE: 1000
        }
        max_allowed = limits.get(tier, 5)
        return min(v, max_allowed)


class TenantAwareAgentConfig(BaseModel):
    """Конфигурация агента с учетом тенанта"""
    tenant_id: str = Field(..., description="ID тенанта-владельца")
    agent_id: str = Field(..., description="ID агента (уникальный в рамках тенанта)")
    name: str = Field(..., description="Имя агента")
    description: Optional[str] = None
    instructions: Optional[str] = None
    
    # Видимость и доступ
    is_public: bool = Field(default=False, description="Доступен ли агент другим тенантам")
    shared_with_tenants: List[str] = Field(default_factory=list, description="Список тенантов с доступом")
    
    # Конфигурации
    model_config: Dict[str, Any] = Field(default_factory=dict)
    tools_config: List[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]] = Field(
        default_factory=list,
        description="Типизированная конфигурация инструментов"
    )
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Метаданные
    created_by: str = Field(..., description="ID пользователя-создателя")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, description="Версия конфигурации")
    
    @validator('agent_id')
    def validate_agent_id(cls, v, values):
        """Валидация ID агента"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Agent ID должен содержать только буквы, цифры, дефисы и подчеркивания")
        return v


class TenantAwareToolConfig(BaseModel):
    """Конфигурация инструмента с учетом тенанта"""
    tenant_id: str = Field(..., description="ID тенанта-владельца")
    tool_id: str = Field(..., description="ID инструмента")
    name: str = Field(..., description="Имя инструмента")
    description: Optional[str] = None
    function_name: str = Field(..., description="Имя функции")
    
    # Безопасность
    code: str = Field(..., description="Python код инструмента")
    is_validated: bool = Field(default=False, description="Прошел ли код валидацию")
    validation_errors: List[str] = Field(default_factory=list)
    
    # Параметры
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    
    # Видимость
    is_public: bool = Field(default=False)
    shared_with_tenants: List[str] = Field(default_factory=list)
    
    # Метаданные
    created_by: str = Field(..., description="ID пользователя-создателя")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentChangeEvent(BaseModel):
    """Событие изменения агента"""
    event_type: Literal["created", "updated", "deleted", "activated", "deactivated"] = Field(..., description="Тип события")
    agent_id: str = Field(..., description="ID агента")
    tenant_id: str = Field(..., description="ID тенанта")
    user_id: Optional[str] = Field(None, description="ID пользователя, инициировавшего изменение")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные детали события")


class ToolChangeEvent(BaseModel):
    """Событие изменения инструмента"""
    event_type: Literal["created", "updated", "deleted", "validated", "validation_failed"] = Field(..., description="Тип события")
    tool_id: str = Field(..., description="ID инструмента")
    tenant_id: str = Field(..., description="ID тенанта")
    user_id: Optional[str] = Field(None, description="ID пользователя")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class SaaSMetrics(BaseModel):
    """Метрики SaaS платформы"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Общие метрики
    total_tenants: int = Field(default=0)
    active_tenants_24h: int = Field(default=0)
    total_agents: int = Field(default=0)
    total_tools: int = Field(default=0)
    
    # Метрики по тенантам
    agents_per_tenant: Dict[str, int] = Field(default_factory=dict)
    tools_per_tenant: Dict[str, int] = Field(default_factory=dict)
    api_calls_per_tenant: Dict[str, int] = Field(default_factory=dict)
    
    # Производительность
    avg_agent_response_time: float = Field(default=0.0)
    cache_hit_rate: float = Field(default=0.0)
    error_rate: float = Field(default=0.0)
    
    # Безопасность
    validation_failures_24h: int = Field(default=0)
    sandbox_violations_24h: int = Field(default=0)
    
    # Использование ресурсов
    cpu_usage_percent: float = Field(default=0.0)
    memory_usage_percent: float = Field(default=0.0)
    db_connections_active: int = Field(default=0)


class TenantUsageStats(BaseModel):
    """Статистика использования тенанта"""
    tenant_id: str = Field(..., description="ID тенанта")
    period_start: datetime = Field(..., description="Начало периода")
    period_end: datetime = Field(..., description="Конец периода")
    
    # Использование
    total_agent_runs: int = Field(default=0)
    total_tool_calls: int = Field(default=0)
    total_api_calls: int = Field(default=0)
    
    # Время выполнения
    total_execution_time_seconds: float = Field(default=0.0)
    avg_response_time_ms: float = Field(default=0.0)
    
    # Ошибки
    total_errors: int = Field(default=0)
    error_rate_percent: float = Field(default=0.0)
    
    # Лимиты
    quota_usage_percent: float = Field(default=0.0)
    rate_limit_hits: int = Field(default=0)


class SecurityAuditLog(BaseModel):
    """Лог аудита безопасности"""
    tenant_id: str = Field(..., description="ID тенанта")
    user_id: Optional[str] = Field(None, description="ID пользователя")
    action: str = Field(..., description="Выполненное действие")
    resource_type: Literal["agent", "tool", "team", "workflow"] = Field(..., description="Тип ресурса")
    resource_id: str = Field(..., description="ID ресурса")
    
    # Детали
    ip_address: Optional[str] = Field(None, description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User Agent")
    success: bool = Field(..., description="Успешность операции")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    
    # Контекст безопасности
    code_executed: Optional[str] = Field(None, description="Выполненный код (для инструментов)")
    validation_result: Optional[Dict[str, Any]] = Field(None, description="Результат валидации")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HotReloadConfig(BaseModel):
    """Конфигурация горячей перезагрузки"""
    enabled: bool = Field(default=True, description="Включена ли горячая перезагрузка")
    cache_ttl_seconds: int = Field(default=300, description="TTL кэша в секундах")
    max_reload_attempts: int = Field(default=3, description="Максимальное количество попыток перезагрузки")
    reload_delay_seconds: int = Field(default=1, description="Задержка между попытками")
    
    # Настройки уведомлений
    enable_db_notifications: bool = Field(default=True, description="Использовать PostgreSQL NOTIFY")
    enable_redis_pubsub: bool = Field(default=False, description="Использовать Redis pub/sub")
    notification_channels: List[str] = Field(default_factory=lambda: ["agent_changes", "tool_changes"])
    
    # Настройки безопасности
    validate_before_reload: bool = Field(default=True, description="Валидировать перед перезагрузкой")
    rollback_on_error: bool = Field(default=True, description="Откатывать изменения при ошибке")


class PlatformConfig(BaseModel):
    """Общая конфигурация платформы"""
    platform_name: str = Field(default="Agent API Platform")
    version: str = Field(default="1.0.0")
    
    # Настройки по умолчанию
    default_subscription_tier: SubscriptionTier = Field(default=SubscriptionTier.FREE)
    default_agent_model: str = Field(default="gpt-4.1")
    
    # Лимиты платформы
    max_tenants: Optional[int] = Field(default=None, description="Максимальное количество тенантов")
    max_agents_per_platform: Optional[int] = Field(default=None)
    max_tools_per_platform: Optional[int] = Field(default=None)
    
    # Настройки безопасности
    require_code_validation: bool = Field(default=True)
    enable_audit_logging: bool = Field(default=True)
    max_code_execution_time_seconds: int = Field(default=30)
    
    # Настройки производительности
    hot_reload: HotReloadConfig = Field(default_factory=HotReloadConfig)
    enable_metrics_collection: bool = Field(default=True)
    metrics_retention_days: int = Field(default=30)


 