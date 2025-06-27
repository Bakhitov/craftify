# API Endpoints Documentation

Полная документация всех API эндпоинтов проекта Agent API и базового фреймворка Agno с примерами запросов.

## Содержание

1. [Здоровье системы](#health-endpoints)
2. [Статические агенты](#static-agents-endpoints)
3. [Динамические агенты](#dynamic-agents-endpoints)
4. [Динамические инструменты](#dynamic-tools-endpoints)
5. [MCP инструменты](#mcp-tools-endpoints)

---

## Health Endpoints

### GET `/v1/health`
Проверка состояния API.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/health"
```

**Пример ответа:**
```json
{
  "status": "success"
}
```

---

## Static Agents Endpoints

### GET `/v1/agents`
Получить список всех доступных статических агентов.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/agents"
```

**Пример ответа:**
```json
[
  "agno_assist",
  "finance_agent", 
  "web_agent"
]
```

### POST `/v1/agents/{agent_id}/runs`
Отправить сообщение агенту и получить ответ.

**Параметры пути:**
- `agent_id` (string): ID агента

**Тело запроса:**
```json
{
  "message": "string",
  "stream": false,
  "model": "gpt-4.1",
  "user_id": "optional_string",
  "session_id": "optional_string"
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/agents/agno_assist/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Как дела?",
    "stream": false,
    "model": "gpt-4.1",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

**Пример ответа (без streaming):**
```json
"Привет! У меня всё отлично, спасибо за вопрос. Чем могу помочь?"
```

**Пример запроса со streaming:**
```bash
curl -X POST "http://localhost:8000/v1/agents/agno_assist/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Расскажи о погоде",
    "stream": true,
    "model": "gpt-4.1"
  }'
```

**Ответ:** Streaming response с chunks текста.

### POST `/v1/agents/{agent_id}/runs/multipart`
Отправить сообщение с файлами агенту и получить ответ. Поддерживает загрузку файлов через multipart/form-data.

**Параметры пути:**
- `agent_id` (string): ID агента

**Тело запроса (multipart/form-data):**
- `message` (string): Текстовое сообщение для агента
- `stream` (boolean, optional): Включить потоковый ответ (по умолчанию false)
- `model` (string, optional): Модель для использования (по умолчанию "gpt-4.1")
- `user_id` (string, optional): ID пользователя
- `session_id` (string, optional): ID сессии
- `files` (array of files, optional): Файлы для обработки (PDF, текст, код, документы)
- `images` (array of files, optional): Изображения для анализа (PNG, JPEG, WebP, GIF)
- `audio` (array of files, optional): Аудио файлы для обработки
- `videos` (array of files, optional): Видео файлы для анализа

**Поддерживаемые форматы файлов:**
- **Документы**: PDF, TXT, MD, HTML, CSS, RTF, CSV, XML
- **Код**: Python (.py), JavaScript (.js), и другие текстовые файлы
- **Изображения**: PNG, JPEG, WebP, GIF
- **Аудио**: Большинство популярных форматов
- **Видео**: MP4, MOV, AVI, MKV, WebM и другие

**Пример запроса с curl:**
```bash
curl -X POST "http://localhost:8000/v1/agents/web_agent/runs/multipart" \
  -F "message=Проанализируй этот документ и найди ключевые моменты" \
  -F "stream=false" \
  -F "model=gpt-4.1" \
  -F "user_id=user123" \
  -F "session_id=session456" \
  -F "files=@document.pdf" \
  -F "images=@chart.png"
```

**Пример запроса с JavaScript (FormData):**
```javascript
const formData = new FormData();
formData.append('message', 'Анализируй загруженные файлы');
formData.append('stream', 'false');
formData.append('model', 'gpt-4.1');
formData.append('files', fileInput.files[0]); // PDF или текстовый файл
formData.append('images', imageInput.files[0]); // Изображение

fetch('/v1/agents/web_agent/runs/multipart', {
  method: 'POST',
  body: formData
}).then(response => response.text());
```

**Пример ответа (без streaming):**
```json
"Анализ документа показал следующие ключевые моменты:
1. Основная тема документа касается...
2. На изображении представлена диаграмма, которая показывает...
3. Рекомендации по улучшению..."
```

**Пример запроса со streaming:**
```bash
curl -X POST "http://localhost:8000/v1/agents/agno_assist/runs/multipart" \
  -F "message=Опиши что ты видишь на изображении" \
  -F "stream=true" \
  -F "images=@photo.jpg"
```

**Ответ:** Streaming response с chunks текста в формате text/event-stream.

### POST `/v1/agents/{agent_id}/knowledge/load`
Загрузить базу знаний для агента.

**Параметры пути:**
- `agent_id` (string): ID агента

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/agents/agno_assist/knowledge/load"
```

**Пример ответа:**
```json
{
  "message": "Knowledge base for agno_assist loaded successfully."
}
```

---

## Dynamic Agents Endpoints

### GET `/v1/dynamic-agents`
Получить список всех динамических агентов.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/dynamic-agents"
```

**Пример ответа:**
```json
[
  {
    "id": 1,
    "name": "Помощник покупателя",
    "agent_id": "shopping_assistant",
    "description": "Агент для помощи с покупками",
    "instructions": "Помогай пользователям выбирать товары",
    "model_id": "gpt-4o",
    "model_config_data": {
      "model": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "tools_config": [
      {
        "type": "static",
        "name": "search_products"
      }
    ],
    "knowledge_config": {},
    "memory_config": {},
    "storage_config": {},
    "settings": {},
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### GET `/v1/dynamic-agents/{agent_id}`
Получить информацию о конкретном динамическом агенте.

**Параметры пути:**
- `agent_id` (string): ID агента

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/dynamic-agents/shopping_assistant"
```

**Пример ответа:** Аналогичен ответу выше для одного агента.

### POST `/v1/dynamic-agents`
Создать нового динамического агента.

**Тело запроса:**
```json
{
  "name": "string",
  "agent_id": "string",
  "description": "optional_string",
  "instructions": "optional_string", 
  "model_id": "gpt-4o",
  "tools_config": [
    {
      "type": "static",
      "name": "tool_name"
    },
    {
      "type": "dynamic", 
      "tool_id": "custom_tool_id"
    },
    {
      "type": "mcp",
      "server_config": {
        "command": "python weather_server.py",
        "env": {}
      }
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "storage_config": {}
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Помощник по кулинарии",
    "agent_id": "cooking_assistant",
    "description": "Агент для помощи с рецептами и готовкой",
    "instructions": "Предлагай рецепты и советы по готовке",
    "model_id": "gpt-4o",
    "tools_config": [
      {
        "type": "static",
        "name": "recipe_search"
      }
    ],
    "max_tokens": 1500,
    "temperature": 0.8
  }'
```

**Пример ответа:** Созданный агент в том же формате, что и GET ответы.

### PUT `/v1/dynamic-agents/{agent_id}`
Обновить существующего динамического агента.

**Параметры пути:**
- `agent_id` (string): ID агента

**Тело запроса:** Аналогично POST запросу.

**Пример запроса:**
```bash
curl -X PUT "http://localhost:8000/v1/dynamic-agents/cooking_assistant" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Профессиональный шеф-помощник",
    "agent_id": "cooking_assistant",
    "description": "Профессиональный агент для кулинарных советов",
    "instructions": "Давай профессиональные советы по готовке",
    "model_id": "gpt-4o",
    "temperature": 0.9
  }'
```

### DELETE `/v1/dynamic-agents/{agent_id}`
Удалить динамического агента.

**Параметры пути:**
- `agent_id` (string): ID агента

**Пример запроса:**
```bash
curl -X DELETE "http://localhost:8000/v1/dynamic-agents/cooking_assistant"
```

**Ответ:** Status 204 No Content

### POST `/v1/dynamic-agents/{agent_id}/activate`
Активировать динамического агента.

**Параметры пути:**
- `agent_id` (string): ID агента

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/dynamic-agents/cooking_assistant/activate"
```

**Пример ответа:**
```json
{
  "message": "Агент cooking_assistant успешно активирован"
}
```

---

## Dynamic Tools Endpoints

### GET `/v1/dynamic-tools`
Получить список всех динамических инструментов.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/dynamic-tools"
```

**Пример ответа:**
```json
[
  {
    "id": 1,
    "name": "Калькулятор",
    "tool_id": "calculator",
    "description": "Выполняет математические вычисления",
    "function_name": "calculate",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "Математическое выражение"
        }
      },
      "required": ["expression"]
    },
    "implementation": "def calculate(expression: str) -> str:\n    return str(eval(expression))",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### GET `/v1/dynamic-tools/{tool_id}`
Получить информацию о конкретном динамическом инструменте.

**Параметры пути:**
- `tool_id` (string): ID инструмента

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/dynamic-tools/calculator"
```

**Пример ответа:** Аналогичен ответу выше для одного инструмента.

### POST `/v1/dynamic-tools/validate`
Валидировать код инструмента перед созданием.

**Тело запроса:**
```json
{
  "name": "string",
  "tool_id": "string",
  "description": "optional_string",
  "function_name": "string",
  "parameters_schema": {},
  "implementation": "string"
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/dynamic-tools/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый калькулятор",
    "tool_id": "test_calc",
    "function_name": "calculate",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "expression": {"type": "string"}
      }
    },
    "implementation": "def calculate(expression: str) -> str:\n    return str(eval(expression))"
  }'
```

**Пример ответа:**
```json
{
  "valid": true,
  "message": "Код инструмента валиден"
}
```

### POST `/v1/dynamic-tools`
Создать новый динамический инструмент.

**Тело запроса:** Аналогично валидации.

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/dynamic-tools" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Генератор UUID",
    "tool_id": "uuid_generator",
    "description": "Генерирует уникальные идентификаторы",
    "function_name": "generate_uuid",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "count": {
          "type": "integer",
          "description": "Количество UUID для генерации",
          "default": 1
        }
      }
    },
    "implementation": "import uuid\n\ndef generate_uuid(count: int = 1) -> list:\n    return [str(uuid.uuid4()) for _ in range(count)]"
  }'
```

### PUT `/v1/dynamic-tools/{tool_id}`
Обновить существующий динамический инструмент.

**Параметры пути:**
- `tool_id` (string): ID инструмента

**Тело запроса:** Аналогично POST запросу.

### DELETE `/v1/dynamic-tools/{tool_id}`
Удалить динамический инструмент.

**Параметры пути:**
- `tool_id` (string): ID инструмента

**Пример запроса:**
```bash
curl -X DELETE "http://localhost:8000/v1/dynamic-tools/uuid_generator"
```

**Ответ:** Status 204 No Content

---

## MCP Tools Endpoints

### GET `/v1/mcp/status`
Получить статус поддержки MCP.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/mcp/status"
```

**Пример ответа:**
```json
{
  "mcp_available": true,
  "supported_transports": ["stdio", "sse", "http"],
  "message": "MCP поддерживается"
}
```

### POST `/v1/mcp/test/stdio`
Тестировать MCP stdio сервер.

**Тело запроса:**
```json
{
  "command": "string",
  "env": {},
  "include_tools": ["optional_list"],
  "exclude_tools": ["optional_list"],
  "timeout": 30
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/mcp/test/stdio" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "python weather_server.py",
    "env": {
      "API_KEY": "your_api_key"
    },
    "timeout": 30
  }'
```

**Пример ответа:**
```json
{
  "server_type": "stdio",
  "tools": [
    {
      "name": "get_weather",
      "description": "Получить информацию о погоде",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string"}
        }
      }
    }
  ],
  "status": "success",
  "error": null
}
```

### POST `/v1/mcp/test/sse`
Тестировать MCP SSE сервер.

**Тело запроса:**
```json
{
  "url": "string",
  "headers": {},
  "include_tools": ["optional_list"],
  "exclude_tools": ["optional_list"],
  "timeout": 30.0
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/mcp/test/sse" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "http://localhost:3000/sse",
    "headers": {
      "Authorization": "Bearer token"
    }
  }'
```

### POST `/v1/mcp/test/http`
Тестировать MCP HTTP сервер.

**Тело запроса:**
```json
{
  "url": "string",
  "headers": {},
  "include_tools": ["optional_list"],
  "exclude_tools": ["optional_list"],
  "timeout": 30.0
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/v1/mcp/test/http" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "http://localhost:3000/mcp",
    "headers": {
      "X-API-Key": "your_key"
    }
  }'
```

### POST `/v1/mcp/test/stdio/call`
Вызвать конкретный инструмент MCP stdio сервера.

**Тело запроса:**
```json
{
  "command": "python weather_server.py",
  "env": {},
  "tool_name": "get_weather",
  "arguments": {
    "city": "Moscow"
  }
}
```

### GET `/v1/mcp/examples`
Получить примеры конфигураций MCP.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/mcp/examples"
```

### GET `/v1/mcp/docs`
Получить документацию по MCP.

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/mcp/docs"
```

---

## Новые эндпоинты агентов

### GET `/v1/agents/{agent_id}/sessions`
Получение сессий для конкретного агента (добавлен аналогично native Agno).

**Параметры пути:**
- `agent_id` (string): ID агента

**Параметры запроса:**
- `user_id` (optional string): ID пользователя для фильтрации

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/v1/agents/agno_assist/sessions?user_id=user123"
```

**Пример ответа:**
```json
{
  "agent_id": "agno_assist",
  "user_id": "user123",
  "sessions": [
    {
      "session_id": "session_123",
      "user_id": "user123",
      "agent_id": "agno_assist",
      "created_at": 1642284600,
      "updated_at": 1642284800,
      "session_data": {
        "session_name": "Чат с агентом",
        "session_state": {}
      },
      "agent_data": {
        "model": "gpt-4.1",
        "name": "Agno Assist"
      }
    }
  ],
  "total_sessions": 1,
  "agent_type": "static",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Информация об изменениях

**Удалены эндпоинты из `agno_base.py`:**

Следующие эндпоинты были перенесены в playground фреймворка Agno согласно архитектуре:

- `GET /playground/status` - статус playground
- `GET /playground/agents` - список агентов для playground
- `POST /playground/agents/{agent_id}/runs` - запуск агента в playground
- `GET /playground/agents/{agent_id}/sessions` - сессии агента в playground  
- `GET /status` - общий статус API

Эти эндпоинты должны обрабатываться нативным playground фреймворка Agno, а не нашей надстройкой.

---

## Примечания

1. **Авторизация**: Некоторые эндпоинты требуют авторизации через заголовок `Authorization: Bearer YOUR_TOKEN`.

2. **Версионирование**: Все эндпоинты используют версию `/v1` или `/v2` в соответствии со стандартами Agno.

3. **Ошибки**: API возвращает стандартные HTTP коды ошибок:
   - `400` - Неверный запрос
   - `401` - Не авторизован  
   - `404` - Не найдено
   - `500` - Внутренняя ошибка сервера
   - `501` - Не реализовано

4. **Streaming**: Для streaming ответов используйте `"stream": true` в запросах к агентам.

5. **Content-Type**: Все POST/PUT запросы должны использовать `Content-Type: application/json`.