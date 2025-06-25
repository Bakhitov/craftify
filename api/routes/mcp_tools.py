"""
API endpoints для управления MCP инструментами.
Обеспечивает создание, тестирование и управление MCP серверами.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from agents.tools.mcp_wrapper import (
    create_mcp_stdio_tools,
    create_mcp_sse_tools,
    create_mcp_http_tools,
    MCP_AVAILABLE
)
from api.middleware.supabase_auth import get_current_user

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])


class MCPStdioConfig(BaseModel):
    """Конфигурация MCP stdio инструмента"""
    command: str = Field(..., description="Команда для запуска MCP сервера")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Переменные окружения")
    include_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для включения")
    exclude_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для исключения")
    timeout: int = Field(default=30, description="Таймаут в секундах")


class MCPSSEConfig(BaseModel):
    """Конфигурация MCP SSE инструмента"""
    url: str = Field(..., description="URL для подключения к SSE серверу")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP заголовки")
    include_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для включения")
    exclude_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для исключения")
    timeout: float = Field(default=30.0, description="Таймаут в секундах")


class MCPHTTPConfig(BaseModel):
    """Конфигурация MCP HTTP инструмента"""
    url: str = Field(..., description="URL для подключения к HTTP серверу")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP заголовки")
    include_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для включения")
    exclude_tools: Optional[List[str]] = Field(default=None, description="Список инструментов для исключения")
    timeout: float = Field(default=30.0, description="Таймаут в секундах")


class MCPToolInfo(BaseModel):
    """Информация о MCP инструменте"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MCPServerInfo(BaseModel):
    """Информация о MCP сервере"""
    server_type: str
    tools: List[MCPToolInfo]
    status: str
    error: Optional[str] = None


@router.get("/status")
async def get_mcp_status():
    """Получает статус MCP поддержки"""
    return {
        "mcp_available": MCP_AVAILABLE,
        "supported_transports": ["stdio", "sse", "http"] if MCP_AVAILABLE else [],
        "message": "MCP поддерживается" if MCP_AVAILABLE else "MCP не установлен"
    }


@router.post("/test/stdio")
async def test_mcp_stdio(
    config: MCPStdioConfig,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Тестирует MCP stdio сервер"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=400, detail="MCP не установлен")
    
    try:
        # Создаем MCP stdio инструменты
        mcp_tools = create_mcp_stdio_tools(
            command=config.command,
            env=config.env,
            include_tools=config.include_tools,
            exclude_tools=config.exclude_tools
        )
        
        # Инициализируем асинхронно
        async with mcp_tools as initialized_tools:
            # Получаем список инструментов
            tools = initialized_tools.get_tools()
            
            tool_info = []
            for tool in tools:
                tool_info.append(MCPToolInfo(
                    name=tool.name,
                    description=tool.description,
                    parameters=getattr(tool, 'parameters', {})
                ))
            
            return MCPServerInfo(
                server_type="stdio",
                tools=tool_info,
                status="success",
                error=None
            )
    
    except Exception as e:
        return MCPServerInfo(
            server_type="stdio",
            tools=[],
            status="error",
            error=str(e)
        )


@router.post("/test/sse")
async def test_mcp_sse(
    config: MCPSSEConfig,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Тестирует MCP SSE сервер"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=400, detail="MCP не установлен")
    
    try:
        # Создаем MCP SSE инструменты
        mcp_tools = create_mcp_sse_tools(
            url=config.url,
            headers=config.headers,
            include_tools=config.include_tools,
            exclude_tools=config.exclude_tools
        )
        
        # Инициализируем асинхронно
        async with mcp_tools as initialized_tools:
            # Получаем список инструментов
            tools = initialized_tools.get_tools()
            
            tool_info = []
            for tool in tools:
                tool_info.append(MCPToolInfo(
                    name=tool.name,
                    description=tool.description,
                    parameters=getattr(tool, 'parameters', {})
                ))
            
            return MCPServerInfo(
                server_type="sse",
                tools=tool_info,
                status="success",
                error=None
            )
    
    except Exception as e:
        return MCPServerInfo(
            server_type="sse",
            tools=[],
            status="error",
            error=str(e)
        )


@router.post("/test/http")
async def test_mcp_http(
    config: MCPHTTPConfig,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Тестирует MCP HTTP сервер"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=400, detail="MCP не установлен")
    
    try:
        # Создаем MCP HTTP инструменты
        mcp_tools = create_mcp_http_tools(
            url=config.url,
            headers=config.headers,
            include_tools=config.include_tools,
            exclude_tools=config.exclude_tools
        )
        
        # Инициализируем асинхронно
        async with mcp_tools as initialized_tools:
            # Получаем список инструментов
            tools = initialized_tools.get_tools()
            
            tool_info = []
            for tool in tools:
                tool_info.append(MCPToolInfo(
                    name=tool.name,
                    description=tool.description,
                    parameters=getattr(tool, 'parameters', {})
                ))
            
            return MCPServerInfo(
                server_type="http",
                tools=tool_info,
                status="success",
                error=None
            )
    
    except Exception as e:
        return MCPServerInfo(
            server_type="http",
            tools=[],
            status="error",
            error=str(e)
        )


class MCPToolTestRequest(BaseModel):
    """Запрос на тестирование MCP инструмента"""
    tool_name: str = Field(..., description="Имя инструмента для тестирования")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Аргументы для вызова инструмента")


@router.post("/test/stdio/call")
async def test_mcp_stdio_tool_call(
    config: MCPStdioConfig,
    test_request: MCPToolTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Тестирует вызов конкретного MCP stdio инструмента"""
    if not MCP_AVAILABLE:
        raise HTTPException(status_code=400, detail="MCP не установлен")
    
    try:
        # Создаем MCP stdio инструменты
        mcp_tools = create_mcp_stdio_tools(
            command=config.command,
            env=config.env,
            include_tools=config.include_tools,
            exclude_tools=config.exclude_tools
        )
        
        # Инициализируем асинхронно
        async with mcp_tools as initialized_tools:
            # Получаем список инструментов
            tools = initialized_tools.get_tools()
            
            # Находим нужный инструмент
            target_tool = None
            for tool in tools:
                if tool.name == test_request.tool_name:
                    target_tool = tool
                    break
            
            if not target_tool:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Инструмент '{test_request.tool_name}' не найден"
                )
            
            # Вызываем инструмент
            result = await target_tool.entrypoint(**test_request.arguments)
            
            return {
                "tool_name": test_request.tool_name,
                "arguments": test_request.arguments,
                "result": result,
                "status": "success"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        return {
            "tool_name": test_request.tool_name,
            "arguments": test_request.arguments,
            "result": None,
            "status": "error",
            "error": str(e)
        }


@router.get("/examples")
async def get_mcp_examples():
    """Возвращает примеры конфигурации MCP серверов"""
    return {
        "stdio_weather_server": {
            "type": "stdio",
            "command": "python examples/weather_mcp_server.py",
            "env": {
                "WEATHER_API_KEY": "your_api_key_here"
            },
            "include_tools": ["get_weather", "get_forecast"],
            "description": "Пример MCP сервера для получения погоды"
        },
        "sse_example": {
            "type": "sse",
            "url": "http://localhost:8080/sse",
            "headers": {
                "Authorization": "Bearer your_token_here"
            },
            "description": "Пример SSE MCP сервера"
        },
        "http_example": {
            "type": "http",
            "url": "http://localhost:8080/mcp",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer your_token_here"
            },
            "description": "Пример HTTP MCP сервера"
        }
    }


@router.get("/docs")
async def get_mcp_documentation():
    """Возвращает документацию по MCP интеграции"""
    return {
        "title": "MCP (Model Context Protocol) Integration",
        "description": "Интеграция с MCP серверами для расширения возможностей агентов",
        "transports": {
            "stdio": {
                "description": "Запуск MCP сервера как подпроцесса",
                "parameters": {
                    "command": "Команда для запуска сервера",
                    "env": "Переменные окружения",
                    "include_tools": "Список инструментов для включения",
                    "exclude_tools": "Список инструментов для исключения"
                },
                "example": {
                    "command": "python mcp_server.py",
                    "env": {"API_KEY": "your_key"}
                }
            },
            "sse": {
                "description": "Подключение к MCP серверу через Server-Sent Events",
                "parameters": {
                    "url": "URL SSE endpoint",
                    "headers": "HTTP заголовки",
                    "include_tools": "Список инструментов для включения",
                    "exclude_tools": "Список инструментов для исключения"
                },
                "example": {
                    "url": "http://localhost:8080/sse",
                    "headers": {"Authorization": "Bearer token"}
                }
            },
            "http": {
                "description": "Подключение к MCP серверу через HTTP",
                "parameters": {
                    "url": "URL HTTP endpoint",
                    "headers": "HTTP заголовки",
                    "include_tools": "Список инструментов для включения",
                    "exclude_tools": "Список инструментов для исключения"
                },
                "example": {
                    "url": "http://localhost:8080/mcp",
                    "headers": {"Content-Type": "application/json"}
                }
            }
        },
        "usage_in_agents": {
            "description": "Использование MCP инструментов в динамических агентах",
            "example": {
                "tools_config": [
                    {
                        "type": "mcp",
                        "transport": "stdio",
                        "command": "python weather_server.py",
                        "env": {"API_KEY": "key"},
                        "include_tools": ["get_weather"]
                    }
                ]
            }
        }
    } 