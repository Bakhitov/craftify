# Craftify - Agent API Platform

Современная платформа для создания и управления AI агентами, построенная как надстройка над фреймворком [Agno](https://github.com/agno-agi/agno).

## 🚀 Особенности

### Гибридная архитектура
- **Статические агенты** - предопределенные агенты из файлов
- **Динамические агенты** - создаваемые и управляемые через базу данных
- **Горячая перезагрузка** - обновление без перезапуска сервера

### Расширенные возможности
- **MCP интеграция** - поддержка Model Context Protocol
- **Система кэширования** - оптимизация производительности
- **Мультитенантность** - изоляция между пользователями
- **Playground совместимость** - работа с Agno Playground

### Безопасность
- Валидация пользовательского кода
- Sandbox выполнение
- Аудит операций

## 📋 Требования

- Python 3.12+
- PostgreSQL (рекомендуется Supabase)
- Docker (опционально)
- Redis (опционально, для кэширования)

## 🛠 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/Bakhitov/craftify.git
cd craftify
```

### 2. Настройка окружения
```bash
# Копируем файл конфигурации
cp example.env .env

# Редактируем .env файл с вашими настройками
nano .env
```

### 3. Запуск через Docker
```bash
# Сборка и запуск контейнера
docker compose up -d --build

# Ожидание запуска (медленный старт ~1 минута)
sleep 60

# Проверка работоспособности
curl http://localhost:8000/v1/health
```

### 4. Применение миграций
```bash
# Применение миграций базы данных
cd db/migrations && alembic upgrade head
```

## 📚 API Документация

После запуска сервера документация доступна по адресам:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Основные эндпоинты

#### Статические агенты
```bash
# Список агентов
GET /v1/agents

# Запуск агента
POST /v1/agents/{agent_id}/runs
```

#### Динамические агенты
```bash
# CRUD операции
GET /v1/dynamic-agents
POST /v1/dynamic-agents
PUT /v1/dynamic-agents/{agent_id}
DELETE /v1/dynamic-agents/{agent_id}
```

#### Управление кэшем
```bash
# Обновление кэша
POST /v1/cache/refresh/all
GET /v1/cache/stats
```

## 🧪 Тестирование

Полный тест-план доступен в файле [TESTING_PLAN.md](TESTING_PLAN.md).

### Быстрые тесты
```bash
# Проверка здоровья API
curl -X GET "http://localhost:8000/v1/health"

# Получение списка агентов
curl -X GET "http://localhost:8000/v1/agents"

# Тестирование web_agent
curl -X POST "http://localhost:8000/v1/agents/web_agent/runs" \
  -H "Content-Type: application/json" \
  -d '{"message": "Привет!", "stream": false}'
```

## 🏗 Архитектура

```
craftify/
├── agents/                 # Агенты
│   ├── static/            # Статические агенты
│   ├── dynamic/           # Фабрики динамических агентов
│   ├── registry/          # Реестр агентов
│   └── cache/             # Система кэширования
├── api/                   # FastAPI приложение
│   ├── routes/            # API роуты
│   └── middleware/        # Middleware
├── db/                    # База данных
│   └── migrations/        # Alembic миграции
└── examples/              # Примеры использования
```

## 🔧 Конфигурация

### Переменные окружения
```env
# База данных
DB_URL=postgresql://user:pass@host:port/db
DB_USER=postgres
DB_PASSWORD=your_password

# API ключи
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Redis (опционально)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token
```

## 📖 Примеры использования

### Создание динамического агента
```python
import requests

agent_data = {
    "name": "Мой Агент",
    "agent_id": "my_agent",
    "description": "Персональный помощник",
    "instructions": "Ты дружелюбный помощник",
    "model_config": {
        "provider": "openai",
        "model": "gpt-4.1"
    }
}

response = requests.post(
    "http://localhost:8000/v1/dynamic-agents",
    json=agent_data
)
```

### Запуск агента
```python
run_data = {
    "message": "Расскажи анекдот",
    "stream": False
}

response = requests.post(
    "http://localhost:8000/v1/agents/my_agent/runs",
    json=run_data
)

print(response.text)
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [Agno Framework](https://github.com/agno-agi/agno) - базовый фреймворк для AI агентов
- [FastAPI](https://fastapi.tiangolo.com/) - современный веб-фреймворк
- [Supabase](https://supabase.com/) - открытая альтернатива Firebase

## 📞 Поддержка

Если у вас есть вопросы или проблемы:
- Создайте [Issue](https://github.com/Bakhitov/craftify/issues)
- Обратитесь к [документации](TESTING_PLAN.md)
- Изучите [примеры](examples/)

---

Made with ❤️ by [Bakhitov](https://github.com/Bakhitov)
