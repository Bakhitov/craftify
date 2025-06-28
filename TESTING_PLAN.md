# Полный тест-план для Agent API Platform

## Анализ архитектуры проекта (ОБНОВЛЕНО)

### Обзор платформы
Agent API Platform - это надстройка над фреймворком Agno, обеспечивающая гибкую архитектуру с поддержкой:
- **Статических агентов** - предопределенные агенты, работающие напрямую из файлов
- **Динамических агентов** - агенты, создаваемые и управляемые через базу данных  
- **Системы кэширования** - TTL-кэш с автоматическим обновлением при изменениях
- **MCP инструментов** - интеграция с Model Context Protocol
- **Динамических инструментов** - пользовательские инструменты через БД
- **Мультимедиа поддержка** - обработка файлов, изображений, аудио, видео

### Ключевые принципы архитектуры (ПРОВЕРЕНО)
1. **Изоляция от Agno** - минимальные изменения через патчи и адаптер совместимости
2. **Горячая перезагрузка** - автоматическое обновление кэша при CRUD операциях
3. **TTL кэширование** - простой и надежный кэш с автоочисткой
4. **Безопасность** - AST валидация кода и ограниченное пространство выполнения
5. **Pydantic валидация** - типизированные модели для всех API

### Архитектурные компоненты (ДЕТАЛИЗИРОВАНО)

#### 1. Ядро системы
- **`agents/selector.py`** - единая точка доступа к агентам
- **`agents/registry/agent_registry.py`** - центральный реестр с кэшированием
- **`agents/factory/agno_compatibility_adapter.py`** - адаптер совместимости с Agno

#### 2. Система кэширования
- **`agents/cache/cache_manager.py`** - TTL-кэш с метриками
- **`agents/cache/auto_refresh.py`** - автообновление при изменениях
- **`agents/cache/event_bus.py`** - система событий (базовая)

#### 3. Динамические компоненты  
- **`agents/dynamic/agent_factory.py`** - фабрика динамических агентов
- **`agents/dynamic/tool_factory.py`** - фабрика динамических инструментов

#### 4. Патчи и совместимость
- **`agents/patches/agno_audio_fix.py`** - исправление AudioArtifact проблем
- **`api/main.py`** - применение патчей при запуске

## Настройка тестовой среды

### 1. Запуск через Docker
```bash
# Копируем переменные окружения
cp example.env .env

# Запускаем контейнер (медленный старт ~1 минута)
docker compose up -d --build

# Ждем запуска сервера (ВАЖНО: проект имеет медленный старт)
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

#### 2.1 Получение списка агентов (проверка bulk операций и кэширования)
```bash
# Получить список всех доступных агентов с полной информацией
# ВАЖНО: Тестируем bulk операции и отсутствие N+1 запросов
curl -X GET "http://localhost:8000/v1/agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив со статическими и динамическими агентами
# Включает: id, name, agent_id, description, model_config, tools_config и др.
# Статические агенты имеют agent_type: "static", editable: false
# Динамические агенты загружаются одним SQL запросом
```

#### 2.2 Проверка кэширования списка агентов
```bash
# Первый запрос (должен быть медленнее - загрузка из БД)
time curl -X GET "http://localhost:8000/v1/agents" -H "Content-Type: application/json" > /dev/null

# Второй запрос (должен быть быстрее - из кэша)
time curl -X GET "http://localhost:8000/v1/agents" -H "Content-Type: application/json" > /dev/null

# Разница во времени должна быть заметной
```

#### 2.3 Запуск статического агента (синхронный)
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
# Проверяем что используются DuckDuckGoTools из Agno
```

#### 2.4 Запуск статического агента (потоковый)
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
# Проверяем что поток корректно завершается
```

#### 2.5 Запуск agno_assist с загрузкой знаний
```bash
# Загрузка базы знаний для agno_assist
curl -X POST "http://localhost:8000/v1/agents/agno_assist/knowledge/load" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "message": "Knowledge base for agno_assist loaded successfully."
# }
```

#### 2.6 Тест мультимедиа загрузки (multipart/form-data)
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
# Проверяем что файл корректно обрабатывается Agno
```

#### 2.7 Получение сессий агента
```bash
# Получить сессии для пользователя
curl -X GET "http://localhost:8000/v1/agents/web_agent/sessions?user_id=test_user_123" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: список сессий пользователя
# Проверяем интеграцию с PostgresAgentStorage
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
# Проверяем что auto_refresh.py корректно очищает "agents:list" и "agents:full_list"
```

#### 3.4 Получение конкретного динамического агента
```bash
# Получить агента по ID
curl -X GET "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: полная информация об агенте
# Проверяем что используется кэшированная конфигурация из agent_factory
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
# ВАЖНО: Проверить что кэш конфигурации очистился в agent_factory
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
# Проверяем что агент создается через agno_adapter.create_agent_safely()
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
# Проверяем AST валидацию и безопасность кода
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
# Проверяем метрики: cache_hits, cache_misses, hit_rate
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

## Специальные тесты архитектуры

### Тест 1: Проверка изоляции от Agno
```bash
# Проверяем что агенты создаются через адаптер совместимости
curl -X GET "http://localhost:8000/v1/cache/stats" | jq '.agno_adapter_info'

# Должен показать информацию о совместимости с Agno
```

### Тест 2: Проверка патчей Agno
```bash
# Создаем агента с аудио (должно работать без ошибок благодаря патчу)
curl -X POST "http://localhost:8000/v1/agents/agno_assist/runs/multipart" \
  -F "message=Тест аудио патча" \
  -F "audio=@/dev/null"

# Не должно быть AudioArtifact ошибок
```

### Тест 3: Проверка bulk операций
```bash
# Измеряем время загрузки списка агентов
time curl -X GET "http://localhost:8000/v1/agents" > /dev/null

# Должно быть быстро даже с большим количеством динамических агентов
```

### Тест 4: Проверка TTL кэша
```bash
# Получаем статистику кэша
curl -X GET "http://localhost:8000/v1/cache/stats"

# Ждем истечения TTL (по умолчанию 5 минут для списка агентов)
sleep 301

# Проверяем что expired_keys увеличился
curl -X GET "http://localhost:8000/v1/cache/stats"
```

## Критерии успешности тестов

### 1. Основная функциональность
- ✅ Все эндпоинты отвечают корректно
- ✅ Статические агенты работают из коробки через агентский реестр
- ✅ Динамические агенты создаются через фабрику и выполняются
- ✅ Мультимедиа файлы обрабатываются через Agno
- ✅ Сессии сохраняются через PostgresAgentStorage

### 2. Автообновление кэша
- ✅ Создание агента → агент сразу доступен в /v1/agents
- ✅ Обновление агента → изменения сразу видны
- ✅ Создание инструмента → инструмент сразу доступен
- ✅ Статистика кэша обновляется в реальном времени
- ✅ auto_refresh.py корректно очищает кэш

### 3. Производительность
- ✅ Ответы агентов приходят в разумное время (<30 сек)
- ✅ Кэш показывает высокий hit rate после прогрева
- ✅ Потоковые ответы работают корректно
- ✅ Bulk операции избегают N+1 запросов

### 4. Безопасность и валидация
- ✅ Некорректные данные отклоняются с понятными ошибками
- ✅ Код инструментов валидируется перед сохранением
- ✅ MCP инструменты работают в изолированной среде
- ✅ Pydantic модели корректно валидируют данные

### 5. Интеграция с Agno
- ✅ Статические агенты используют стандартные Agno компоненты
- ✅ Динамические агенты совместимы с Agno API через адаптер
- ✅ Патчи применяются корректно при запуске
- ✅ agno_adapter.create_agent_safely() работает корректно

### 6. Архитектурная целостность
- ✅ Селектор агентов правильно делегирует в реестр
- ✅ Фабрика агентов использует кэширование конфигураций
- ✅ TTL кэш работает стабильно и показывает метрики
- ✅ Автообновление кэша срабатывает при CRUD операциях

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

### 6. Проблемы с адаптером совместимости
- **Симптом**: Ошибки при создании агентов
- **Решение**: Проверить agno_adapter.filter_agent_params()

### 7. Проблемы с патчами Agno
- **Симптом**: AudioArtifact ошибки при загрузке сессий
- **Решение**: Проверить что apply_agno_patches() вызывается при запуске

## Заключение

Данный тест-план покрывает все основные компоненты Agent API Platform:
- Статические и динамические агенты
- Систему TTL кэширования с автообновлением
- Динамические инструменты
- MCP интеграцию
- Мультимедиа обработку
- Изоляцию от Agno через адаптер совместимости
- Bulk операции для производительности

Особое внимание уделяется тестированию автоматического обновления кэша и архитектурной целостности платформы.

**Архитектура проекта в целом реализована правильно** с использованием лучших практик:
- Изоляция от Agno через адаптер
- TTL кэширование с автообновлением  
- Pydantic валидация
- Bulk операции для производительности
- Правильное использование фабричного паттерна 