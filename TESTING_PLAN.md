# Полный тест-план для Agent API Platform

## Анализ архитектуры проекта

### Обзор платформы
Agent API Platform - это надстройка над фреймворком Agno, обеспечивающая гибкую архитектуру с поддержкой:
- **Статических агентов** - предопределенные агенты, работающие напрямую из файлов
- **Динамических агентов** - агенты, создаваемые и управляемые через базу данных
- **Системы кэширования** - автоматическое обновление кэша при изменениях
- **MCP инструментов** - интеграция с Model Context Protocol
- **Динамических инструментов** - пользовательские инструменты через БД
- **Мультимедиа поддержка** - обработка файлов, изображений, аудио, видео

### Ключевые принципы архитектуры
1. **Изоляция от Agno** - минимальные изменения в базовом фреймворке через патчи
2. **Горячая перезагрузка** - автоматическое обновление кэша при CRUD операциях
3. **Event-driven кэширование** - система событий для обновления кэша
4. **Безопасность** - валидация кода и sandbox выполнение
5. **Pydantic валидация** - типизированные модели для всех API

## Настройка тестовой среды

### 1. Запуск через Docker
```bash
# Копируем переменные окружения
cp example.env .env

# Запускаем контейнер (медленный старт ~1 минута)
docker compose up -d --build

# Ждем запуска сервера
sleep 60

# Проверяем статус
curl -X GET "http://localhost:8000/v1/health"
```

### 2. Применение миграций
```bash
# Применяем миграции базы данных
cd db/migrations && alembic upgrade head
```

## Тестирование эндпоинтов

### 1. Health Check - Проверка работоспособности

```bash
# Основная проверка здоровья API
curl -X GET "http://localhost:8000/v1/health" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success"
# }
```

### 2. Статические агенты - /v1/agents

#### 2.1 Получение списка агентов (проверка кэширования)
```bash
# Получить список всех доступных агентов с полной информацией
curl -X GET "http://localhost:8000/v1/agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив со статическими и динамическими агентами
# Включает: id, name, agent_id, description, model_config, tools_config и др.
```

#### 2.2 Запуск статического агента (синхронный)
```bash
# Запуск web_agent с простым сообщением
curl -X POST "http://localhost:8000/v1/agents/web_agent/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Найди информацию о последних новостях в области AI",
    "stream": false,
    "model": "gpt-4.1",
    "user_id": "test_user_123",
    "session_id": "test_session_456"
  }'

# Ожидаемый ответ: текстовый ответ агента с результатами поиска
```

#### 2.3 Запуск статического агента (потоковый)
```bash
# Запуск finance_agent в потоковом режиме
curl -X POST "http://localhost:8000/v1/agents/finance_agent/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Проанализируй текущую ситуацию на рынке криптовалют",
    "stream": true,
    "model": "gpt-4.1",
    "user_id": "test_user_123",
    "session_id": "test_session_789"
  }'

# Ожидаемый ответ: Server-Sent Events поток с частями ответа
```

#### 2.4 Запуск agno_assist с загрузкой знаний
```bash
# Загрузка базы знаний для agno_assist
curl -X POST "http://localhost:8000/v1/agents/agno_assist/knowledge/load" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "message": "Knowledge base for agno_assist loaded successfully."
# }
```

#### 2.5 Тест мультимедиа загрузки (multipart/form-data)
```bash
# Создаем тестовый файл
echo "Тестовый документ для агента" > test_document.txt

# Запуск агента с файлом
curl -X POST "http://localhost:8000/v1/agents/agno_assist/runs/multipart" \
  -F "message=Проанализируй этот документ" \
  -F "stream=false" \
  -F "model=gpt-4.1" \
  -F "user_id=test_user_123" \
  -F "session_id=test_session_multipart" \
  -F "files=@test_document.txt"

# Ожидаемый ответ: анализ документа
```

#### 2.6 Получение сессий агента
```bash
# Получить сессии для пользователя
curl -X GET "http://localhost:8000/v1/agents/web_agent/sessions?user_id=test_user_123" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: список сессий пользователя
```

### 3. Динамические агенты - /v1/dynamic-agents

#### 3.1 Получение списка динамических агентов
```bash
# Получить все динамические агенты
curl -X GET "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив объектов DynamicAgentResponse
```

#### 3.2 Создание динамического агента (проверка автообновления кэша)
```bash
# Создание нового динамического агента
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый Агент",
    "agent_id": "test_dynamic_agent",
    "description": "Агент для тестирования API",
    "instructions": "Ты помощник для тестирования. Отвечай кратко и по делу.",
    "model_id": "gpt-4.1",
    "tools_config": [],
    "knowledge_config": {},
    "memory_config": {},
    "storage_config": {},
    "settings": {}
  }'

# Ожидаемый ответ: созданный агент с ID и временными метками
# ВАЖНО: Проверить что кэш обновился автоматически!
```

#### 3.3 Проверка автообновления кэша после создания
```bash
# Сразу после создания проверяем что агент доступен в общем списке
curl -X GET "http://localhost:8000/v1/agents" \
  -H "Content-Type: application/json" | grep "test_dynamic_agent"

# Должен найти созданного агента - кэш обновился автоматически
```

#### 3.4 Получение конкретного динамического агента
```bash
# Получить агента по ID
curl -X GET "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: полная информация об агенте
```

#### 3.5 Обновление динамического агента (проверка кэша)
```bash
# Обновление существующего агента
curl -X PUT "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Обновленный Тестовый Агент",
    "agent_id": "test_dynamic_agent",
    "description": "Обновленное описание агента",
    "instructions": "Ты обновленный помощник. Теперь отвечай более подробно.",
    "model_id": "gpt-4.1",
    "tools_config": [],
    "knowledge_config": {},
    "memory_config": {},
    "storage_config": {},
    "settings": {}
  }'

# Ожидаемый ответ: обновленный агент
# ВАЖНО: Проверить что кэш обновился автоматически!
```

#### 3.6 Активация/деактивация агента
```bash
# Активация агента
curl -X POST "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent/activate" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: подтверждение активации
```

#### 3.7 Тестирование динамического агента
```bash
# Запуск созданного динамического агента
curl -X POST "http://localhost:8000/v1/agents/test_dynamic_agent/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Это тест динамического агента.",
    "stream": false,
    "model": "gpt-4.1",
    "user_id": "test_user_dynamic",
    "session_id": "test_session_dynamic"
  }'

# Ожидаемый ответ: ответ от динамического агента
```

### 4. Динамические инструменты - /v1/dynamic-tools

#### 4.1 Получение списка динамических инструментов
```bash
# Получить все динамические инструменты
curl -X GET "http://localhost:8000/v1/dynamic-tools/" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив инструментов или пустой массив
```

#### 4.2 Валидация кода инструмента
```bash
# Валидация кода перед созданием
curl -X POST "http://localhost:8000/v1/dynamic-tools/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый инструмент",
    "tool_id": "test_tool",
    "description": "Простой инструмент для тестирования",
    "function_name": "test_function",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Сообщение для обработки"
        }
      },
      "required": ["message"]
    },
    "implementation": "def test_function(message: str) -> str:\n    return f\"Processed: {message}\""
  }'

# Ожидаемый ответ: {"valid": true, "message": "..."}
```

#### 4.3 Создание динамического инструмента (проверка автообновления кэша)
```bash
# Создание нового инструмента
curl -X POST "http://localhost:8000/v1/dynamic-tools/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый инструмент",
    "tool_id": "test_tool",
    "description": "Простой инструмент для тестирования",
    "function_name": "test_function",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Сообщение для обработки"
        }
      },
      "required": ["message"]
    },
    "implementation": "def test_function(message: str) -> str:\n    return f\"Processed: {message}\""
  }'

# Ожидаемый ответ: созданный инструмент
# ВАЖНО: Проверить что кэш инструментов обновился автоматически!
```

#### 4.4 Получение конкретного инструмента
```bash
# Получить инструмент по ID
curl -X GET "http://localhost:8000/v1/dynamic-tools/test_tool" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: полная информация об инструменте
```

#### 4.5 Обновление динамического инструмента
```bash
# Обновление существующего инструмента
curl -X PUT "http://localhost:8000/v1/dynamic-tools/test_tool" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Обновленный тестовый инструмент",
    "tool_id": "test_tool",
    "description": "Обновленное описание инструмента",
    "function_name": "test_function",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Сообщение для обработки"
        }
      },
      "required": ["message"]
    },
    "implementation": "def test_function(message: str) -> str:\n    return f\"Updated processed: {message.upper()}\""
  }'

# Ожидаемый ответ: обновленный инструмент
```

### 5. MCP инструменты - /v1/mcp

#### 5.1 Проверка статуса MCP
```bash
# Проверить статус MCP поддержки
curl -X GET "http://localhost:8000/v1/mcp/status" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: информация о доступности MCP
```

#### 5.2 Получение примеров MCP
```bash
# Получить примеры конфигураций MCP
curl -X GET "http://localhost:8000/v1/mcp/examples" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: примеры конфигураций для stdio, sse, http
```

#### 5.3 Получение документации MCP
```bash
# Получить документацию по MCP
curl -X GET "http://localhost:8000/v1/mcp/docs" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: документация по использованию MCP
```

#### 5.4 Тестирование MCP STDIO (если доступно)
```bash
# Тест MCP STDIO сервера (пример с weather сервером)
curl -X POST "http://localhost:8000/v1/mcp/test/stdio" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python examples/weather_mcp_server.py",
    "env": {},
    "include_tools": null,
    "exclude_tools": null,
    "timeout": 30
  }'

# Ожидаемый ответ: информация о доступных инструментах MCP или ошибка
```

### 6. Система кэширования - /v1/cache

#### 6.1 Получение статистики кэша
```bash
# Получить детальную статистику кэша
curl -X GET "http://localhost:8000/v1/cache/stats" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: статистика cache_manager, auto_refresh и health
```

#### 6.2 Проверка здоровья кэша
```bash
# Проверить здоровье системы кэширования
curl -X GET "http://localhost:8000/v1/cache/health" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: состояние кэша и автообновления
```

#### 6.3 Ручное обновление кэша
```bash
# Ручное обновление всего кэша
curl -X POST "http://localhost:8000/v1/cache/refresh" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: результат операции обновления
```

#### 6.4 Обновление кэша конкретного агента
```bash
# Обновить кэш конкретного агента
curl -X POST "http://localhost:8000/v1/cache/refresh/agent/web_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: результат обновления кэша агента
```

#### 6.5 Очистка истекших элементов кэша
```bash
# Очистить истекшие элементы кэша
curl -X POST "http://localhost:8000/v1/cache/cleanup" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: количество очищенных элементов
```

#### 6.6 Демонстрация автообновления кэша
```bash
# Получить информацию о системе автообновления
curl -X GET "http://localhost:8000/v1/cache/demo" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: описание функций автообновления
```

## Тестирование автообновления кэша

### Сценарий 1: Создание динамического агента
```bash
# 1. Получить текущий список агентов
curl -X GET "http://localhost:8000/v1/agents" | jq '.[] | .agent_id'

# 2. Создать нового динамического агента
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cache Test Agent",
    "agent_id": "cache_test_agent",
    "description": "Агент для тестирования кэша",
    "instructions": "Ты тестовый агент для проверки кэширования.",
    "model_id": "gpt-4.1"
  }'

# 3. СРАЗУ проверить что агент появился в списке (кэш обновился автоматически)
curl -X GET "http://localhost:8000/v1/agents" | grep "cache_test_agent"

# 4. Проверить статистику кэша
curl -X GET "http://localhost:8000/v1/cache/stats"
```

### Сценарий 2: Обновление динамического агента
```bash
# 1. Обновить агента
curl -X PUT "http://localhost:8000/v1/dynamic-agents/cache_test_agent" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Cache Test Agent",
    "agent_id": "cache_test_agent",
    "description": "Обновленный агент для тестирования кэша",
    "instructions": "Ты обновленный тестовый агент.",
    "model_id": "gpt-4.1"
  }'

# 2. СРАЗУ проверить что изменения отражены в списке
curl -X GET "http://localhost:8000/v1/agents" | grep -A5 -B5 "cache_test_agent"

# 3. Запустить агента чтобы убедиться что он работает с новой конфигурацией
curl -X POST "http://localhost:8000/v1/agents/cache_test_agent/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Проверяем обновленного агента.",
    "stream": false
  }'
```

### Сценарий 3: Создание и использование динамического инструмента
```bash
# 1. Создать инструмент
curl -X POST "http://localhost:8000/v1/dynamic-tools/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Text Processor",
    "tool_id": "text_processor",
    "description": "Обрабатывает текст",
    "function_name": "process_text",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "Текст для обработки"}
      },
      "required": ["text"]
    },
    "implementation": "def process_text(text: str) -> str:\n    return text.upper()"
  }'

# 2. Создать агента с этим инструментом
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent with Tool",
    "agent_id": "agent_with_tool",
    "description": "Агент с пользовательским инструментом",
    "instructions": "Используй инструмент text_processor для обработки текста.",
    "model_id": "gpt-4.1",
    "tools_config": [
      {
        "type": "dynamic",
        "tool_id": "text_processor"
      }
    ]
  }'

# 3. Протестировать агента с инструментом
curl -X POST "http://localhost:8000/v1/agents/agent_with_tool/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Обработай текст: hello world",
    "stream": false
  }'
```

## Критерии успешности тестов

### 1. Основная функциональность
- ✅ Все эндпоинты отвечают корректно
- ✅ Статические агенты работают из коробки
- ✅ Динамические агенты создаются и выполняются
- ✅ Мультимедиа файлы обрабатываются
- ✅ Сессии сохраняются и восстанавливаются

### 2. Автообновление кэша
- ✅ Создание агента → агент сразу доступен в /v1/agents
- ✅ Обновление агента → изменения сразу видны
- ✅ Создание инструмента → инструмент сразу доступен
- ✅ Статистика кэша обновляется в реальном времени

### 3. Производительность
- ✅ Ответы агентов приходят в разумное время (<30 сек)
- ✅ Кэш показывает высокий hit rate после прогрева
- ✅ Потоковые ответы работают корректно

### 4. Безопасность и валидация
- ✅ Некорректные данные отклоняются с понятными ошибками
- ✅ Код инструментов валидируется перед сохранением
- ✅ MCP инструменты работают в изолированной среде

### 5. Интеграция с Agno
- ✅ Статические агенты используют стандартные Agno компоненты
- ✅ Динамические агенты совместимы с Agno API
- ✅ Патчи применяются корректно при запуске

## Возможные проблемы и решения

### 1. Проблемы с базой данных
- **Симптом**: Ошибки 500 при работе с динамическими агентами
- **Решение**: Проверить подключение к PostgreSQL и выполнить миграции

### 2. Проблемы с кэшированием
- **Симптом**: Созданные агенты не появляются в списке
- **Решение**: Проверить работу auto_cache и event_bus

### 3. Проблемы с MCP
- **Симптом**: MCP инструменты недоступны
- **Решение**: Установить пакет mcp или отключить MCP функциональность

### 4. Проблемы с мультимедиа
- **Симптом**: Файлы не обрабатываются
- **Решение**: Проверить поддержку ffmpeg и OpenAI Whisper

### 5. Медленные ответы агентов
- **Симптом**: Агенты отвечают дольше 30 секунд
- **Решение**: Проверить настройки OpenAI API и модели

## Заключение

Данный тест-план покрывает все основные компоненты Agent API Platform:
- Статические и динамические агенты
- Систему кэширования с автообновлением
- Динамические инструменты
- MCP интеграцию
- Мультимедиа обработку

Особое внимание уделяется тестированию автоматического обновления кэша, что является ключевой особенностью платформы. 