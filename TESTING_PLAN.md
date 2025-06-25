# Полный тест-план для Agent API Platform

## Анализ архитектуры проекта

### Обзор платформы
Agent API Platform - это надстройка над фреймворком Agno, обеспечивающая гибкую архитектуру с поддержкой:
- **Статических агентов** - предопределенные агенты, работающие напрямую из файлов
- **Динамических агентов** - агенты, создаваемые и управляемые через базу данных
- **Системы кэширования** - для оптимизации производительности
- **MCP инструментов** - интеграция с Model Context Protocol
- **Playground интеграции** - совместимость с Agno Playground

### Ключевые принципы архитектуры
1. **Изоляция от Agno** - минимальные изменения в базовом фреймворке
2. **Горячая перезагрузка** - динамическое обновление без перезапуска
3. **Мультитенантность** - поддержка изоляции между тенантами
4. **Безопасность** - валидация кода и sandbox выполнение

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

#### 2.1 Получение списка агентов
```bash
# Получить список всех доступных агентов
curl -X GET "http://localhost:8000/v1/agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# ["web_agent", "agno_assist", "finance_agent", "dynamic_agent_1", ...]
```

#### 2.2 Запуск агента (синхронный)
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

#### 2.3 Запуск агента (потоковый)
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

#### 2.4 Загрузка базы знаний агента
```bash
# Загрузка базы знаний для agno_assist
curl -X POST "http://localhost:8000/v1/agents/agno_assist/knowledge/load" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "message": "Knowledge base for agno_assist loaded successfully."
# }
```

### 3. Динамические агенты - /v1/dynamic-agents

#### 3.1 Получение списка динамических агентов
```bash
# Получить все динамические агенты
curl -X GET "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив объектов DynamicAgentResponse
```

#### 3.2 Создание динамического агента
```bash
# Создание нового динамического агента
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый Агент",
    "agent_id": "test_dynamic_agent",
    "description": "Агент для тестирования API",
    "instructions": "Ты помощник для тестирования. Отвечай кратко и по делу.",
    "model_config": {
      "provider": "openai",
      "model": "gpt-4.1",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "tools_config": [],
    "knowledge_config": {
      "enabled": false
    },
    "memory_config": {
      "enabled": true,
      "memory_type": "simple"
    },
    "storage_config": {
      "enabled": false
    },
    "settings": {
      "stream": true,
      "debug_mode": true,
      "markdown": true
    }
  }'

# Ожидаемый ответ: созданный агент с ID и временными метками
```

#### 3.3 Получение конкретного динамического агента
```bash
# Получить агента по ID
curl -X GET "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: полная информация об агенте
```

#### 3.4 Обновление динамического агента
```bash
# Обновление существующего агента
curl -X PUT "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Обновленный Тестовый Агент",
    "agent_id": "test_dynamic_agent",
    "description": "Обновленное описание агента",
    "instructions": "Ты обновленный помощник. Теперь отвечай более подробно.",
    "model_config": {
      "provider": "openai",
      "model": "gpt-4.1",
      "temperature": 0.5,
      "max_tokens": 1500
    },
    "tools_config": [],
    "knowledge_config": {
      "enabled": false
    },
    "memory_config": {
      "enabled": true,
      "memory_type": "simple"
    },
    "storage_config": {
      "enabled": false
    },
    "settings": {
      "stream": true,
      "debug_mode": false,
      "markdown": true
    }
  }'

# Ожидаемый ответ: обновленная информация об агенте
```

#### 3.5 Активация динамического агента
```bash
# Активация агента
curl -X POST "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent/activate" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "message": "Динамический агент test_dynamic_agent активирован",
#   "agent_id": "test_dynamic_agent"
# }
```

#### 3.6 Обновление кэша агентов
```bash
# Обновление кэша всех агентов
curl -X POST "http://localhost:8000/v1/dynamic-agents/refresh-cache" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "message": "Кэш агентов обновлен",
#   "refreshed_count": 5
# }
```

#### 3.7 Удаление динамического агента
```bash
# Удаление агента
curl -X DELETE "http://localhost:8000/v1/dynamic-agents/test_dynamic_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: HTTP 204 No Content
```

### 4. Динамические инструменты - /v1/dynamic-tools

#### 4.1 Получение списка инструментов
```bash
# Получить все динамические инструменты
curl -X GET "http://localhost:8000/v1/dynamic-tools/" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: массив объектов ToolResponse
```

#### 4.2 Валидация кода инструмента
```bash
# Валидация кода перед созданием
curl -X POST "http://localhost:8000/v1/dynamic-tools/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Калькулятор",
    "tool_id": "calculator_tool",
    "description": "Простой калькулятор для математических операций",
    "function_name": "calculate",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "Математическое выражение для вычисления"
        }
      },
      "required": ["expression"]
    },
    "implementation": "def calculate(expression: str) -> str:\n    try:\n        result = eval(expression)\n        return f\"Результат: {result}\"\n    except Exception as e:\n        return f\"Ошибка: {str(e)}\""
  }'

# Ожидаемый ответ:
# {
#   "valid": true,
#   "message": "Код инструмента валиден"
# }
```

#### 4.3 Создание динамического инструмента
```bash
# Создание нового инструмента после валидации
curl -X POST "http://localhost:8000/v1/dynamic-tools/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Калькулятор",
    "tool_id": "calculator_tool",
    "description": "Простой калькулятор для математических операций",
    "function_name": "calculate",
    "parameters_schema": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "Математическое выражение для вычисления"
        }
      },
      "required": ["expression"]
    },
    "implementation": "def calculate(expression: str) -> str:\n    try:\n        result = eval(expression)\n        return f\"Результат: {result}\"\n    except Exception as e:\n        return f\"Ошибка: {str(e)}\""
  }'

# Ожидаемый ответ: созданный инструмент с метаданными
```

#### 4.4 Получение конкретного инструмента
```bash
# Получить инструмент по ID
curl -X GET "http://localhost:8000/v1/dynamic-tools/calculator_tool" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: полная информация об инструменте
```

### 5. MCP инструменты - /v1/mcp

#### 5.1 Проверка статуса MCP
```bash
# Проверка поддержки MCP
curl -X GET "http://localhost:8000/v1/mcp/status" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "mcp_available": true,
#   "supported_transports": ["stdio", "sse", "http"],
#   "message": "MCP поддерживается"
# }
```

#### 5.2 Тестирование MCP stdio сервера
```bash
# Тестирование stdio MCP сервера (требуется аутентификация)
curl -X POST "http://localhost:8000/v1/mcp/test/stdio" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{
    "command": "python examples/weather_mcp_server.py",
    "env": {},
    "include_tools": null,
    "exclude_tools": null,
    "timeout": 30
  }'

# Ожидаемый ответ: информация о сервере и доступных инструментах
```

#### 5.3 Получение примеров MCP
```bash
# Получение примеров конфигурации MCP
curl -X GET "http://localhost:8000/v1/mcp/examples" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: примеры конфигураций для разных типов MCP серверов
```

#### 5.4 Получение документации MCP
```bash
# Получение документации по MCP
curl -X GET "http://localhost:8000/v1/mcp/docs" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: документация по использованию MCP
```

### 6. Управление кэшем - /v1/cache

#### 6.1 Обновление кэша конкретного агента
```bash
# Обновление кэша агента
curl -X POST "http://localhost:8000/v1/cache/refresh/agent/web_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Agent web_agent cache refreshed",
#   "agent_id": "web_agent"
# }
```

#### 6.2 Обновление кэша инструмента
```bash
# Обновление кэша инструмента
curl -X POST "http://localhost:8000/v1/cache/refresh/tool/calculator_tool" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Tool calculator_tool cache refreshed",
#   "tool_id": "calculator_tool"
# }
```

#### 6.3 Обновление кэша playground
```bash
# Обновление кэша playground
curl -X POST "http://localhost:8000/v1/cache/refresh/playground" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Playground cache refreshed"
# }
```

#### 6.4 Полное обновление кэша
```bash
# Очистка и обновление всего кэша
curl -X POST "http://localhost:8000/v1/cache/refresh/all" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "All cache cleared and refreshed"
# }
```

#### 6.5 Статистика кэша
```bash
# Получение статистики кэша
curl -X GET "http://localhost:8000/v1/cache/stats" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: детальная статистика использования кэша
```

#### 6.6 Очистка истекших элементов
```bash
# Очистка истекших элементов кэша
curl -X POST "http://localhost:8000/v1/cache/cleanup" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Cleaned up 3 expired entries",
#   "expired_count": 3
# }
```

#### 6.7 Проверка здоровья кэша
```bash
# Проверка состояния системы кэширования
curl -X GET "http://localhost:8000/v1/cache/health" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: информация о состоянии кэша
```

### 7. Playground управление - /v1/playground

#### 7.1 Обновление playground
```bash
# Принудительное обновление playground
curl -X POST "http://localhost:8000/v1/playground/refresh" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Playground refreshed successfully",
#   "agents_count": 8
# }
```

#### 7.2 Обновление конкретного агента в playground
```bash
# Обновление конкретного агента
curl -X POST "http://localhost:8000/v1/playground/refresh/agent/web_agent" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
# {
#   "status": "success",
#   "message": "Agent web_agent refreshed in playground",
#   "agent_id": "web_agent"
# }
```

#### 7.3 Статистика playground
```bash
# Получение статистики playground
curl -X GET "http://localhost:8000/v1/playground/stats" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: статистика агентов в playground
```

### 8. Agno Playground эндпоинты

#### 8.1 Получение агентов для playground
```bash
# Получение списка агентов в формате Agno Playground
curl -X GET "http://localhost:8000/agents" \
  -H "Content-Type: application/json"

# Ожидаемый ответ: агенты в формате, совместимом с Agno Playground
```

#### 8.2 Запуск агента через playground
```bash
# Запуск агента через интерфейс playground
curl -X POST "http://localhost:8000/agents/web_agent/run" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Какая погода сегодня?",
    "stream": false
  }'

# Ожидаемый ответ: ответ агента в формате Agno
```

## Сценарии интеграционного тестирования

### Сценарий 1: Полный жизненный цикл динамического агента
```bash
# 1. Создание агента
AGENT_ID="integration_test_agent"
curl -X POST "http://localhost:8000/v1/dynamic-agents" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Интеграционный Тест Агент\",
    \"agent_id\": \"$AGENT_ID\",
    \"description\": \"Агент для интеграционного тестирования\",
    \"instructions\": \"Ты помощник для интеграционного тестирования.\",
    \"model_config\": {
      \"provider\": \"openai\",
      \"model\": \"gpt-4.1\"
    }
  }"

# 2. Проверка создания
curl -X GET "http://localhost:8000/v1/dynamic-agents/$AGENT_ID"

# 3. Активация
curl -X POST "http://localhost:8000/v1/dynamic-agents/$AGENT_ID/activate"

# 4. Обновление кэша
curl -X POST "http://localhost:8000/v1/dynamic-agents/refresh-cache"

# 5. Тестирование работы через статический API
curl -X POST "http://localhost:8000/v1/agents/$AGENT_ID/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Ты работаешь?",
    "stream": false
  }'

# 6. Удаление
curl -X DELETE "http://localhost:8000/v1/dynamic-agents/$AGENT_ID"
```

### Сценарий 2: Тестирование системы кэширования
```bash
# 1. Получение статистики до операций
curl -X GET "http://localhost:8000/v1/cache/stats"

# 2. Запуск нескольких агентов для заполнения кэша
curl -X POST "http://localhost:8000/v1/agents/web_agent/runs" \
  -d '{"message": "Тест 1", "stream": false}'

curl -X POST "http://localhost:8000/v1/agents/finance_agent/runs" \
  -d '{"message": "Тест 2", "stream": false}'

# 3. Проверка изменения статистики
curl -X GET "http://localhost:8000/v1/cache/stats"

# 4. Очистка кэша
curl -X POST "http://localhost:8000/v1/cache/refresh/all"

# 5. Проверка очистки
curl -X GET "http://localhost:8000/v1/cache/stats"
```

### Сценарий 3: Тестирование производительности
```bash
# Создание нескольких агентов параллельно
for i in {1..5}; do
  curl -X POST "http://localhost:8000/v1/dynamic-agents" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Perf Test Agent $i\",
      \"agent_id\": \"perf_test_$i\",
      \"model_config\": {\"provider\": \"openai\", \"model\": \"gpt-4.1\"}
    }" &
done
wait

# Проверка создания всех агентов
curl -X GET "http://localhost:8000/v1/dynamic-agents" | jq '.[] | select(.name | contains("Perf Test"))'

# Очистка тестовых агентов
for i in {1..5}; do
  curl -X DELETE "http://localhost:8000/v1/dynamic-agents/perf_test_$i" &
done
wait
```

## Ожидаемые результаты и валидация

### Критерии успешного тестирования:
1. **Все health check эндпоинты** возвращают статус "success"
2. **Статические агенты** успешно обрабатывают запросы
3. **Динамические агенты** создаются, обновляются и удаляются корректно
4. **Система кэширования** показывает корректную статистику
5. **MCP интеграция** определяет доступность протокола
6. **Playground** корректно загружает агентов

### Мониторинг производительности:
- Время отклика < 2 секунд для простых запросов
- Время отклика < 30 секунд для сложных запросов с инструментами
- Потребление памяти стабильно
- Отсутствие утечек соединений к БД

### Обработка ошибок:
- Корректные HTTP статус коды
- Информативные сообщения об ошибках
- Graceful degradation при недоступности внешних сервисов

## Заключение

Данный тест-план покрывает все основные функциональности Agent API Platform:
- Полный CRUD для динамических агентов и инструментов
- Интеграцию со статическими агентами Agno
- Систему кэширования и оптимизации производительности
- MCP протокол для расширения функциональности
- Совместимость с Agno Playground

Платформа демонстрирует гибкую архитектуру, позволяющую работать как со статическими, так и с динамическими компонентами, обеспечивая при этом высокую производительность через систему кэширования и изоляцию от базового фреймворка Agno. 