"""
MCP Wrapper для поддержки MCP серверов в динамических агентах.
Обеспечивает интеграцию MCP серверов через различные транспорты.
Следует принципам проекта: минимальное вмешательство, максимальная совместимость с Agno.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from pathlib import Path

from agno.tools.toolkit import Toolkit
from agno.tools.function import Function
from agno.utils.log import log_debug, log_error, log_warning

# Проверяем наличие MCP
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client, get_default_environment
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import Tool as MCPTool, CallToolResult, TextContent, ImageContent, EmbeddedResource
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    log_warning("MCP не установлен. MCP инструменты будут недоступны.")


class MCPStdioWrapper(Toolkit):
    """
    Wrapper для MCP серверов с stdio транспортом.
    Позволяет использовать MCP серверы в динамических агентах.
    Следует принципам Agno: использует стандартные классы без модификации.
    """
    
    def __init__(
        self,
        command: str,
        env: Optional[Dict[str, str]] = None,
        include_tools: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
        name: str = "MCP Stdio Tools",
        timeout: int = 30
    ):
        super().__init__(name=name)
        
        if not MCP_AVAILABLE:
            raise ImportError("MCP не установлен. Установите используя: pip install mcp")
        
        self.command = command
        self.env = env or {}
        self.include_tools = include_tools
        self.exclude_tools = exclude_tools
        self.timeout = timeout
        self._tools_cache = {}
        self._initialized = False
        self._session = None
        self._client_context = None
        self._session_context = None
    
    async def _initialize_mcp_server(self) -> bool:
        """Инициализирует подключение к MCP серверу"""
        try:
            log_debug(f"Инициализация MCP stdio сервера: {self.command}")
            
            # Подготавливаем окружение
            server_env = {
                **get_default_environment(),
                **self.env
            }
            
            # Парсим команду
            from shlex import split
            parts = split(self.command)
            if not parts:
                raise ValueError("Пустая команда")
            
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Создаем параметры сервера
            server_params = StdioServerParameters(
                command=cmd,
                args=args,
                env=server_env
            )
            
            # Создаем клиентский контекст
            self._client_context = stdio_client(server_params)
            
            # Инициализируем соединение
            read, write = await self._client_context.__aenter__()
            
            # Создаем сессию
            self._session_context = ClientSession(read, write)
            self._session = await self._session_context.__aenter__()
            
            # Получаем список инструментов
            tools_response = await self._session.list_tools()
            
            log_debug(f"Найдено {len(tools_response.tools)} MCP инструментов")
            
            # Создаем Function для каждого MCP инструмента
            for mcp_tool in tools_response.tools:
                # Проверяем фильтры
                if self.include_tools and mcp_tool.name not in self.include_tools:
                    continue
                if self.exclude_tools and mcp_tool.name in self.exclude_tools:
                    continue
                
                # Создаем Function используя стандартный класс Agno
                function = self._create_function_from_mcp_tool(mcp_tool)
                if function:
                    self._tools_cache[mcp_tool.name] = function
                    log_debug(f"Создан MCP инструмент: {mcp_tool.name}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            log_error(f"Ошибка инициализации MCP stdio сервера: {e}")
            await self._cleanup()
            return False
    
    def _create_function_from_mcp_tool(self, mcp_tool: MCPTool) -> Optional[Function]:
        """Создает Function из MCP инструмента"""
        try:
            # Создаем entrypoint для вызова MCP инструмента
            async def mcp_entrypoint(**kwargs) -> str:
                return await self._call_mcp_tool(mcp_tool.name, kwargs)
            
            # Конвертируем схему параметров MCP в JSON Schema
            parameters = self._convert_mcp_schema_to_json_schema(mcp_tool.inputSchema)
            
            # Создаем Function используя стандартный класс Agno
            function = Function(
                name=mcp_tool.name,
                description=mcp_tool.description or f"MCP инструмент: {mcp_tool.name}",
                parameters=parameters,
                entrypoint=mcp_entrypoint
            )
            
            return function
            
        except Exception as e:
            log_error(f"Ошибка создания Function из MCP инструмента {mcp_tool.name}: {e}")
            return None
    
    def _convert_mcp_schema_to_json_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует MCP схему в JSON Schema для Agno"""
        if not input_schema:
            return {"type": "object", "properties": {}, "required": []}
        
        # MCP использует JSON Schema, поэтому просто возвращаем как есть
        # с добавлением обязательных полей если их нет
        schema = dict(input_schema)
        
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}
        if "required" not in schema:
            schema["required"] = []
        
        return schema
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызывает MCP инструмент"""
        try:
            if not self._session:
                raise RuntimeError("MCP сессия не инициализирована")
            
            log_debug(f"Вызов MCP инструмента '{tool_name}' с аргументами: {arguments}")
            
            # Вызываем инструмент через MCP
            result: CallToolResult = await self._session.call_tool(tool_name, arguments)
            
            # Обрабатываем ошибки
            if result.isError:
                error_msg = f"Ошибка MCP инструмента '{tool_name}': {result.content}"
                log_error(error_msg)
                return error_msg
            
            # Обрабатываем результат
            response_parts = []
            
            for content_item in result.content:
                if isinstance(content_item, TextContent):
                    response_parts.append(content_item.text)
                elif isinstance(content_item, ImageContent):
                    # Для изображений добавляем описание
                    response_parts.append(f"[Изображение: {getattr(content_item, 'url', 'встроенное')}]")
                elif isinstance(content_item, EmbeddedResource):
                    # Для ресурсов добавляем описание
                    response_parts.append(f"[Ресурс: {content_item.resource}]")
                else:
                    # Для других типов контента
                    response_parts.append(f"[Контент типа: {type(content_item).__name__}]")
            
            result_text = "\n".join(response_parts) if response_parts else "Инструмент выполнен успешно"
            log_debug(f"MCP инструмент '{tool_name}' выполнен успешно")
            
            return result_text
            
        except Exception as e:
            error_msg = f"Ошибка вызова MCP инструмента '{tool_name}': {e}"
            log_error(error_msg)
            return error_msg
    
    async def _cleanup(self):
        """Очищает ресурсы MCP"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                self._session = None
            
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
                self._client_context = None
                
        except Exception as e:
            log_error(f"Ошибка при очистке MCP ресурсов: {e}")
    
    def get_tools(self) -> List[Function]:
        """Возвращает список доступных MCP инструментов"""
        if not self._initialized:
            # Пытаемся инициализировать синхронно (для совместимости)
            try:
                # Создаем новый event loop если его нет
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Инициализируем асинхронно
                success = loop.run_until_complete(self._initialize_mcp_server())
                if not success:
                    log_warning("Не удалось инициализировать MCP сервер")
                    return []
                    
            except Exception as e:
                log_error(f"Ошибка инициализации MCP сервера: {e}")
                return []
        
        return list(self._tools_cache.values())
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_mcp_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()


class MCPSSEWrapper(Toolkit):
    """
    Wrapper для MCP серверов с SSE транспортом.
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        include_tools: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
        name: str = "MCP SSE Tools",
        timeout: float = 30.0
    ):
        super().__init__(name=name)
        
        if not MCP_AVAILABLE:
            raise ImportError("MCP не установлен. Установите используя: pip install mcp")
        
        self.url = url
        self.headers = headers or {}
        self.include_tools = include_tools
        self.exclude_tools = exclude_tools
        self.timeout = timeout
        self._tools_cache = {}
        self._initialized = False
        self._session = None
        self._client_context = None
        self._session_context = None
    
    async def _initialize_mcp_server(self) -> bool:
        """Инициализирует подключение к MCP SSE серверу"""
        try:
            log_debug(f"Инициализация MCP SSE сервера: {self.url}")
            
            # Создаем SSE клиент
            self._client_context = sse_client(
                url=self.url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Инициализируем соединение
            read, write = await self._client_context.__aenter__()
            
            # Создаем сессию
            self._session_context = ClientSession(read, write)
            self._session = await self._session_context.__aenter__()
            
            # Получаем список инструментов
            tools_response = await self._session.list_tools()
            
            log_debug(f"Найдено {len(tools_response.tools)} MCP SSE инструментов")
            
            # Создаем Function для каждого MCP инструмента
            for mcp_tool in tools_response.tools:
                # Проверяем фильтры
                if self.include_tools and mcp_tool.name not in self.include_tools:
                    continue
                if self.exclude_tools and mcp_tool.name in self.exclude_tools:
                    continue
                
                # Создаем Function
                function = self._create_function_from_mcp_tool(mcp_tool)
                if function:
                    self._tools_cache[mcp_tool.name] = function
                    log_debug(f"Создан MCP SSE инструмент: {mcp_tool.name}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            log_error(f"Ошибка инициализации MCP SSE сервера: {e}")
            await self._cleanup()
            return False
    
    def _create_function_from_mcp_tool(self, mcp_tool: MCPTool) -> Optional[Function]:
        """Создает Function из MCP инструмента"""
        try:
            async def mcp_entrypoint(**kwargs) -> str:
                return await self._call_mcp_tool(mcp_tool.name, kwargs)
            
            parameters = self._convert_mcp_schema_to_json_schema(mcp_tool.inputSchema)
            
            function = Function(
                name=mcp_tool.name,
                description=mcp_tool.description or f"MCP SSE инструмент: {mcp_tool.name}",
                parameters=parameters,
                entrypoint=mcp_entrypoint
            )
            
            return function
            
        except Exception as e:
            log_error(f"Ошибка создания Function из MCP SSE инструмента {mcp_tool.name}: {e}")
            return None
    
    def _convert_mcp_schema_to_json_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует MCP схему в JSON Schema"""
        if not input_schema:
            return {"type": "object", "properties": {}, "required": []}
        
        schema = dict(input_schema)
        
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}
        if "required" not in schema:
            schema["required"] = []
        
        return schema
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызывает MCP SSE инструмент"""
        try:
            if not self._session:
                raise RuntimeError("MCP SSE сессия не инициализирована")
            
            log_debug(f"Вызов MCP SSE инструмента '{tool_name}' с аргументами: {arguments}")
            
            result: CallToolResult = await self._session.call_tool(tool_name, arguments)
            
            if result.isError:
                error_msg = f"Ошибка MCP SSE инструмента '{tool_name}': {result.content}"
                log_error(error_msg)
                return error_msg
            
            response_parts = []
            for content_item in result.content:
                if isinstance(content_item, TextContent):
                    response_parts.append(content_item.text)
                elif isinstance(content_item, ImageContent):
                    response_parts.append(f"[Изображение: {getattr(content_item, 'url', 'встроенное')}]")
                elif isinstance(content_item, EmbeddedResource):
                    response_parts.append(f"[Ресурс: {content_item.resource}]")
                else:
                    response_parts.append(f"[Контент типа: {type(content_item).__name__}]")
            
            result_text = "\n".join(response_parts) if response_parts else "SSE инструмент выполнен успешно"
            log_debug(f"MCP SSE инструмент '{tool_name}' выполнен успешно")
            
            return result_text
            
        except Exception as e:
            error_msg = f"Ошибка вызова MCP SSE инструмента '{tool_name}': {e}"
            log_error(error_msg)
            return error_msg
    
    async def _cleanup(self):
        """Очищает ресурсы MCP SSE"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                self._session = None
            
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
                self._client_context = None
                
        except Exception as e:
            log_error(f"Ошибка при очистке MCP SSE ресурсов: {e}")
    
    def get_tools(self) -> List[Function]:
        """Возвращает список доступных MCP SSE инструментов"""
        if not self._initialized:
            try:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                success = loop.run_until_complete(self._initialize_mcp_server())
                if not success:
                    log_warning("Не удалось инициализировать MCP SSE сервер")
                    return []
                    
            except Exception as e:
                log_error(f"Ошибка инициализации MCP SSE сервера: {e}")
                return []
        
        return list(self._tools_cache.values())
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_mcp_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()


class MCPHTTPWrapper(Toolkit):
    """
    Wrapper для MCP серверов с HTTP транспортом.
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        include_tools: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
        name: str = "MCP HTTP Tools",
        timeout: float = 30.0
    ):
        super().__init__(name=name)
        
        if not MCP_AVAILABLE:
            raise ImportError("MCP не установлен. Установите используя: pip install mcp")
        
        self.url = url
        self.headers = headers or {}
        self.include_tools = include_tools
        self.exclude_tools = exclude_tools
        self.timeout = timeout
        self._tools_cache = {}
        self._initialized = False
        self._session = None
        self._client_context = None
        self._session_context = None
    
    async def _initialize_mcp_server(self) -> bool:
        """Инициализирует подключение к MCP HTTP серверу"""
        try:
            log_debug(f"Инициализация MCP HTTP сервера: {self.url}")
            
            from datetime import timedelta
            
            # Создаем HTTP клиент
            self._client_context = streamablehttp_client(
                url=self.url,
                headers=self.headers,
                timeout=timedelta(seconds=self.timeout)
            )
            
            # Инициализируем соединение
            read, write = await self._client_context.__aenter__()
            
            # Создаем сессию
            self._session_context = ClientSession(read, write)
            self._session = await self._session_context.__aenter__()
            
            # Получаем список инструментов
            tools_response = await self._session.list_tools()
            
            log_debug(f"Найдено {len(tools_response.tools)} MCP HTTP инструментов")
            
            # Создаем Function для каждого MCP инструмента
            for mcp_tool in tools_response.tools:
                # Проверяем фильтры
                if self.include_tools and mcp_tool.name not in self.include_tools:
                    continue
                if self.exclude_tools and mcp_tool.name in self.exclude_tools:
                    continue
                
                # Создаем Function
                function = self._create_function_from_mcp_tool(mcp_tool)
                if function:
                    self._tools_cache[mcp_tool.name] = function
                    log_debug(f"Создан MCP HTTP инструмент: {mcp_tool.name}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            log_error(f"Ошибка инициализации MCP HTTP сервера: {e}")
            await self._cleanup()
            return False
    
    def _create_function_from_mcp_tool(self, mcp_tool: MCPTool) -> Optional[Function]:
        """Создает Function из MCP инструмента"""
        try:
            async def mcp_entrypoint(**kwargs) -> str:
                return await self._call_mcp_tool(mcp_tool.name, kwargs)
            
            parameters = self._convert_mcp_schema_to_json_schema(mcp_tool.inputSchema)
            
            function = Function(
                name=mcp_tool.name,
                description=mcp_tool.description or f"MCP HTTP инструмент: {mcp_tool.name}",
                parameters=parameters,
                entrypoint=mcp_entrypoint
            )
            
            return function
            
        except Exception as e:
            log_error(f"Ошибка создания Function из MCP HTTP инструмента {mcp_tool.name}: {e}")
            return None
    
    def _convert_mcp_schema_to_json_schema(self, input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует MCP схему в JSON Schema"""
        if not input_schema:
            return {"type": "object", "properties": {}, "required": []}
        
        schema = dict(input_schema)
        
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}
        if "required" not in schema:
            schema["required"] = []
        
        return schema
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызывает MCP HTTP инструмент"""
        try:
            if not self._session:
                raise RuntimeError("MCP HTTP сессия не инициализирована")
            
            log_debug(f"Вызов MCP HTTP инструмента '{tool_name}' с аргументами: {arguments}")
            
            result: CallToolResult = await self._session.call_tool(tool_name, arguments)
            
            if result.isError:
                error_msg = f"Ошибка MCP HTTP инструмента '{tool_name}': {result.content}"
                log_error(error_msg)
                return error_msg
            
            response_parts = []
            for content_item in result.content:
                if isinstance(content_item, TextContent):
                    response_parts.append(content_item.text)
                elif isinstance(content_item, ImageContent):
                    response_parts.append(f"[Изображение: {getattr(content_item, 'url', 'встроенное')}]")
                elif isinstance(content_item, EmbeddedResource):
                    response_parts.append(f"[Ресурс: {content_item.resource}]")
                else:
                    response_parts.append(f"[Контент типа: {type(content_item).__name__}]")
            
            result_text = "\n".join(response_parts) if response_parts else "HTTP инструмент выполнен успешно"
            log_debug(f"MCP HTTP инструмент '{tool_name}' выполнен успешно")
            
            return result_text
            
        except Exception as e:
            error_msg = f"Ошибка вызова MCP HTTP инструмента '{tool_name}': {e}"
            log_error(error_msg)
            return error_msg
    
    async def _cleanup(self):
        """Очищает ресурсы MCP HTTP"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                self._session = None
            
            if self._client_context:
                await self._client_context.__aexit__(None, None, None)
                self._client_context = None
                
        except Exception as e:
            log_error(f"Ошибка при очистке MCP HTTP ресурсов: {e}")
    
    def get_tools(self) -> List[Function]:
        """Возвращает список доступных MCP HTTP инструментов"""
        if not self._initialized:
            try:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                success = loop.run_until_complete(self._initialize_mcp_server())
                if not success:
                    log_warning("Не удалось инициализировать MCP HTTP сервер")
                    return []
                    
            except Exception as e:
                log_error(f"Ошибка инициализации MCP HTTP сервера: {e}")
                return []
        
        return list(self._tools_cache.values())
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_mcp_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()


# Фабричные функции для создания MCP инструментов
def create_mcp_stdio_tools(
    command: str,
    env: Optional[Dict[str, str]] = None,
    include_tools: Optional[List[str]] = None,
    exclude_tools: Optional[List[str]] = None
) -> MCPStdioWrapper:
    """
    Создает MCP stdio инструменты.
    
    Args:
        command: Команда для запуска MCP сервера
        env: Переменные окружения
        include_tools: Список инструментов для включения
        exclude_tools: Список инструментов для исключения
        
    Returns:
        MCPStdioWrapper экземпляр
    """
    return MCPStdioWrapper(
        command=command,
        env=env,
        include_tools=include_tools,
        exclude_tools=exclude_tools
    )


def create_mcp_sse_tools(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    include_tools: Optional[List[str]] = None,
    exclude_tools: Optional[List[str]] = None
) -> MCPSSEWrapper:
    """
    Создает MCP SSE инструменты.
    
    Args:
        url: URL для подключения к SSE серверу
        headers: HTTP заголовки
        include_tools: Список инструментов для включения
        exclude_tools: Список инструментов для исключения
        
    Returns:
        MCPSSEWrapper экземпляр
    """
    return MCPSSEWrapper(
        url=url,
        headers=headers,
        include_tools=include_tools,
        exclude_tools=exclude_tools
    )


def create_mcp_http_tools(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    include_tools: Optional[List[str]] = None,
    exclude_tools: Optional[List[str]] = None
) -> MCPHTTPWrapper:
    """
    Создает MCP HTTP инструменты.
    
    Args:
        url: URL для подключения к HTTP серверу
        headers: HTTP заголовки
        include_tools: Список инструментов для включения
        exclude_tools: Список инструментов для исключения
        
    Returns:
        MCPHTTPWrapper экземпляр
    """
    return MCPHTTPWrapper(
        url=url,
        headers=headers,
        include_tools=include_tools,
        exclude_tools=exclude_tools
    ) 