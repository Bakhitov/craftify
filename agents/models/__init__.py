"""
Pydantic модели для строгой типизации конфигураций агентов.
Обеспечивают валидацию и типобезопасность для динамических сущностей.
"""

from typing import Dict, Any, List, Optional, Literal, Union, Callable, Type
from pydantic import BaseModel, Field, validator, RootModel


class ModelConfig(BaseModel):
    """Конфигурация модели для агента"""
    type: Literal["openai", "anthropic", "ollama"] = Field(default="openai", description="Тип модели")
    id: str = Field(default="gpt-4.1", description="ID модели")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Температура модели")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="Максимальное количество токенов")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Presence penalty")


class StaticToolConfig(BaseModel):
    """Конфигурация статического инструмента"""
    type: Literal["static"] = "static"
    import_path: str = Field(..., description="Путь импорта инструмента")
    init_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Параметры инициализации")


class DynamicToolConfig(BaseModel):
    """Конфигурация динамического инструмента"""
    type: Literal["dynamic"] = "dynamic"
    tool_id: str = Field(..., description="ID динамического инструмента")


class MCPToolConfig(BaseModel):
    """Конфигурация MCP инструмента"""
    type: Literal["mcp"] = "mcp"
    transport: Literal["stdio", "sse", "http"] = Field(default="stdio", description="Тип транспорта MCP")
    
    # Параметры для stdio транспорта
    command: Optional[str] = Field(default=None, description="Команда для запуска MCP сервера (stdio)")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Переменные окружения (stdio)")
    
    # Параметры для sse/http транспорта
    url: Optional[str] = Field(default=None, description="URL для подключения (sse/http)")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP заголовки (sse/http)")
    
    # Общие параметры
    timeout: Optional[int] = Field(default=5, description="Таймаут подключения в секундах")
    include_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для включения")
    exclude_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для исключения")


class ToolConfig(RootModel[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]]):
    """Общая конфигурация инструмента"""
    root: Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig] = Field(..., discriminator='type')


class MemoryConfig(BaseModel):
    """Конфигурация памяти агента"""
    enabled: bool = Field(default=False, description="Включить память")
    type: Literal["agent", "v2", "postgres"] = Field(default="v2", description="Тип памяти")
    memory_model_config: Optional[ModelConfig] = Field(default=None, description="Конфигурация модели для памяти")
    table_name: str = Field(default="user_memories", description="Имя таблицы для хранения памяти")
    db_schema: str = Field(default="public", description="Схема базы данных")
    delete_memories: bool = Field(default=True, description="Разрешить удаление воспоминаний")
    clear_memories: bool = Field(default=True, description="Разрешить очистку воспоминаний")


class StorageConfig(BaseModel):
    """Конфигурация хранилища агента"""
    enabled: bool = Field(default=True, description="Включить хранилище")
    type: Literal["postgres", "file", "agent"] = Field(default="postgres", description="Тип хранилища")
    table_name: str = Field(default="sessions", description="Имя таблицы для хранения сессий")
    db_schema: str = Field(default="public", description="Схема базы данных")
    db_url: Optional[str] = Field(default=None, description="URL базы данных (если не указан, используется из окружения)")


class KnowledgeConfig(BaseModel):
    """Конфигурация базы знаний агента"""
    enabled: bool = Field(default=False, description="Включить базу знаний")
    type: Literal["url", "document", "text"] = Field(default="url", description="Тип источника знаний")
    sources: List[str] = Field(default_factory=list, description="Источники знаний (URL, пути к файлам, тексты)")
    table_name: str = Field(default="knowledge", description="Имя таблицы для векторного хранилища")
    db_schema: str = Field(default="public", description="Схема базы данных")
    search_type: Literal["vector", "hybrid", "keyword"] = Field(default="hybrid", description="Тип поиска")
    embedder_model: str = Field(default="text-embedding-3-small", description="Модель для эмбеддингов")


class AgentSettings(BaseModel):
    """Полные настройки агента - все параметры из agno.Agent"""
    
    # --- Agent settings ---
    name: Optional[str] = Field(default=None, description="Имя агента")
    introduction: Optional[str] = Field(default=None, description="Введение агента")
    
    # --- User settings ---
    user_id: Optional[str] = Field(default=None, description="ID пользователя по умолчанию")
    
    # --- Session settings ---
    session_name: Optional[str] = Field(default=None, description="Имя сессии")
    search_previous_sessions_history: bool = Field(default=False, description="Поиск по истории предыдущих сессий")
    num_history_sessions: Optional[int] = Field(default=None, description="Количество исторических сессий")
    
    # --- Agent Context ---
    add_context: bool = Field(default=False, description="Добавлять контекст в промпт пользователя")
    resolve_context: bool = Field(default=True, description="Разрешать контекст перед запуском")
    
    # --- Agent Memory ---
    enable_agentic_memory: bool = Field(default=False, description="Включить агентную память (→ update_user_memory)")
    enable_user_memories: bool = Field(default=False, description="Создавать/обновлять пользовательские воспоминания")
    add_memory_references: Optional[bool] = Field(default=None, description="Добавлять ссылки на воспоминания в ответ")
    enable_session_summaries: bool = Field(default=False, description="Создавать/обновлять сводки сессий")
    add_session_summary_references: Optional[bool] = Field(default=None, description="Добавлять ссылки на сводки сессий в ответ")
    
    # --- Agent History ---
    add_history_to_messages: bool = Field(default=False, description="Добавлять историю в сообщения")
    num_history_responses: Optional[int] = Field(default=None, description="Количество исторических ответов (deprecated)")
    num_history_runs: int = Field(default=3, ge=0, le=50, description="Количество исторических запусков")
    
    # --- Agent Knowledge ---
    enable_agentic_knowledge_filters: bool = Field(default=False, description="Позволить агенту выбирать фильтры знаний")
    add_references: bool = Field(default=False, description="Добавлять ссылки на источники знаний")
    references_format: Literal["json", "yaml"] = Field(default="json", description="Формат ссылок")
    
    # --- Agent Tools ---
    show_tool_calls: bool = Field(default=True, description="Показывать вызовы инструментов")
    tool_call_limit: Optional[int] = Field(default=None, description="Максимальное количество вызовов инструментов")
    
    # --- Agent Reasoning ---
    reasoning: bool = Field(default=False, description="Включить пошаговое рассуждение")
    reasoning_min_steps: int = Field(default=1, ge=1, description="Минимальное количество шагов рассуждения")
    reasoning_max_steps: int = Field(default=10, ge=1, description="Максимальное количество шагов рассуждения")
    
    # --- Default tools (встроенные инструменты agno) ---
    read_chat_history: bool = Field(default=False, description="Добавить инструмент get_chat_history")
    search_knowledge: bool = Field(default=True, description="Добавить инструмент search_knowledge_base")
    update_knowledge: bool = Field(default=False, description="Добавить инструмент для обновления базы знаний")
    read_tool_call_history: bool = Field(default=False, description="Добавить инструмент get_tool_call_history")
    
    # --- System message settings ---
    system_message_role: str = Field(default="system", description="Роль системного сообщения")
    create_default_system_message: bool = Field(default=True, description="Создавать системное сообщение по умолчанию")
    
    # --- Settings for building the default system message ---
    description: Optional[str] = Field(default=None, description="Описание агента")
    goal: Optional[str] = Field(default=None, description="Цель задачи")
    instructions: Optional[str] = Field(default=None, description="Инструкции для агента")
    expected_output: Optional[str] = Field(default=None, description="Ожидаемый вывод")
    additional_context: Optional[str] = Field(default=None, description="Дополнительный контекст")
    markdown: bool = Field(default=False, description="Форматировать ответы в markdown")
    add_name_to_instructions: bool = Field(default=False, description="Добавлять имя агента в инструкции")
    add_datetime_to_instructions: bool = Field(default=False, description="Добавлять дату и время в инструкции")
    add_location_to_instructions: bool = Field(default=False, description="Добавлять местоположение в инструкции")
    timezone_identifier: Optional[str] = Field(default=None, description="Идентификатор часового пояса")
    add_state_in_messages: bool = Field(default=False, description="Добавлять состояние сессии в сообщения")
    success_criteria: Optional[str] = Field(default=None, description="Критерии успеха")
    
    # --- User message settings ---
    user_message_role: str = Field(default="user", description="Роль пользовательского сообщения")
    create_default_user_message: bool = Field(default=True, description="Создавать пользовательское сообщение по умолчанию")
    
    # --- Agent Response Settings ---
    retries: int = Field(default=0, ge=0, description="Количество попыток повтора")
    delay_between_retries: int = Field(default=1, ge=0, description="Задержка между повторами (секунды)")
    exponential_backoff: bool = Field(default=False, description="Экспоненциальное увеличение задержки")
    
    # --- Agent Response Model Settings ---
    parse_response: bool = Field(default=True, description="Парсить ответ в модель")
    structured_outputs: Optional[bool] = Field(default=None, description="Использовать структурированные выводы")
    use_json_mode: bool = Field(default=False, description="Использовать JSON режим")
    save_response_to_file: Optional[str] = Field(default=None, description="Сохранять ответ в файл")
    
    # --- Agent Streaming ---
    stream: Optional[bool] = Field(default=None, description="Стриминг ответа")
    stream_intermediate_steps: bool = Field(default=False, description="Стриминг промежуточных шагов")
    
    # --- Events ---
    store_events: bool = Field(default=False, description="Сохранять события")
    
    # --- Agent Team ---
    role: Optional[str] = Field(default=None, description="Роль агента в команде")
    respond_directly: bool = Field(default=False, description="Отвечать напрямую пользователю")
    add_transfer_instructions: bool = Field(default=True, description="Добавлять инструкции для передачи задач")
    team_response_separator: str = Field(default="\n", description="Разделитель ответов команды")
    
    # --- Debug & Monitoring ---
    debug_mode: bool = Field(default=False, description="Режим отладки")
    monitoring: bool = Field(default=False, description="Мониторинг")
    telemetry: bool = Field(default=True, description="Телеметрия")


class TeamMemberConfig(BaseModel):
    """Конфигурация участника команды"""
    agent_id: str = Field(..., description="ID агента-участника")
    role: Optional[str] = Field(default=None, description="Роль в команде")
    respond_directly: bool = Field(default=False, description="Отвечать напрямую пользователю")


class TeamSettings(BaseModel):
    """Настройки команды"""
    mode: Literal["route", "coordinate", "collaborate"] = Field(default="coordinate", description="Режим работы команды")
    markdown: bool = Field(default=False, description="Форматировать ответы в markdown")
    add_datetime_to_instructions: bool = Field(default=False, description="Добавлять дату и время в инструкции")
    share_member_interactions: bool = Field(default=False, description="Делиться взаимодействиями участников")
    enable_agentic_context: bool = Field(default=False, description="Включить агентный контекст")
    stream_member_events: bool = Field(default=True, description="Стримить события участников")
    debug_mode: bool = Field(default=False, description="Режим отладки")
    store_events: bool = Field(default=False, description="Сохранять события")


class WorkflowStepConfig(BaseModel):
    """Конфигурация шага workflow"""
    step_id: str = Field(..., description="ID шага")
    name: str = Field(..., description="Название шага")
    agent_id: Optional[str] = Field(default=None, description="ID агента для шага")
    team_id: Optional[str] = Field(default=None, description="ID команды для шага")
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Условия выполнения шага")
    next_steps: List[str] = Field(default_factory=list, description="Следующие шаги")


class WorkflowSettings(BaseModel):
    """Настройки workflow"""
    debug_mode: bool = Field(default=False, description="Режим отладки")
    monitoring: bool = Field(default=False, description="Мониторинг")
    telemetry: bool = Field(default=True, description="Телеметрия")


# Основные модели для БД
class DynamicAgentConfig(BaseModel):
    """Полная конфигурация динамического агента"""
    name: str = Field(..., description="Имя агента")
    agent_id: str = Field(..., description="Уникальный ID агента")
    description: Optional[str] = Field(default=None, description="Описание агента")
    instructions: Optional[str] = Field(default=None, description="Инструкции для агента")
    
    agent_model_config: ModelConfig = Field(default_factory=ModelConfig, description="Конфигурация модели")
    tools_config: List[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]] = Field(default_factory=list, description="Конфигурация инструментов")
    knowledge_config: KnowledgeConfig = Field(default_factory=KnowledgeConfig, description="Конфигурация знаний")
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig, description="Конфигурация памяти")
    storage_config: StorageConfig = Field(default_factory=StorageConfig, description="Конфигурация хранилища")
    settings: AgentSettings = Field(default_factory=AgentSettings, description="Настройки агента")


class DynamicTeamConfig(BaseModel):
    """Полная конфигурация динамической команды"""
    name: str = Field(..., description="Имя команды")
    team_id: str = Field(..., description="Уникальный ID команды")
    description: Optional[str] = Field(default=None, description="Описание команды")
    
    members_config: List[TeamMemberConfig] = Field(default_factory=list, description="Конфигурация участников")
    settings: TeamSettings = Field(default_factory=TeamSettings, description="Настройки команды")


class DynamicWorkflowConfig(BaseModel):
    """Полная конфигурация динамического workflow"""
    name: str = Field(..., description="Имя workflow")
    workflow_id: str = Field(..., description="Уникальный ID workflow")
    description: Optional[str] = Field(default=None, description="Описание workflow")
    
    steps_config: List[WorkflowStepConfig] = Field(default_factory=list, description="Конфигурация шагов")
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings, description="Настройки workflow")


# Функции валидации
def validate_agent_config(config: Dict[str, Any]) -> DynamicAgentConfig:
    """
    Валидирует конфигурацию агента через Pydantic модели.
    
    Args:
        config: Словарь с конфигурацией агента
        
    Returns:
        Валидированная конфигурация DynamicAgentConfig
        
    Raises:
        ValidationError: При ошибках валидации
    """
    return DynamicAgentConfig(**config)


def validate_model_config(config: Dict[str, Any]) -> ModelConfig:
    """Валидирует конфигурацию модели"""
    return ModelConfig(**config)


def validate_tools_config(config: List[Dict[str, Any]]) -> List[Union[StaticToolConfig, DynamicToolConfig, MCPToolConfig]]:
    """Валидирует конфигурацию инструментов"""
    validated_tools = []
    for tool_config in config:
        tool_type = tool_config.get('type', 'static')
        if tool_type == 'static':
            validated_tools.append(StaticToolConfig(**tool_config))
        elif tool_type == 'dynamic':
            validated_tools.append(DynamicToolConfig(**tool_config))
        elif tool_type == 'mcp':
            validated_tools.append(MCPToolConfig(**tool_config))
    return validated_tools


def validate_memory_config(config: Dict[str, Any]) -> MemoryConfig:
    """Валидирует конфигурацию памяти"""
    return MemoryConfig(**config)


def validate_storage_config(config: Dict[str, Any]) -> StorageConfig:
    """Валидирует конфигурацию хранилища"""
    return StorageConfig(**config)


def validate_knowledge_config(config: Dict[str, Any]) -> KnowledgeConfig:
    """Валидирует конфигурацию базы знаний"""
    return KnowledgeConfig(**config)


def validate_agent_settings(config: Dict[str, Any]) -> AgentSettings:
    """Валидирует настройки агента"""
    return AgentSettings(**config) 