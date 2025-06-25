#!/usr/bin/env python3
"""
Скрипт для тестирования кастомных инструментов и MCP серверов.
Демонстрирует работу с init_params и различными типами инструментов.
"""

import asyncio
import json
import requests
from typing import Dict, Any

# API endpoints
BASE_URL = "http://localhost:8000"

def test_static_tool_with_init_params():
    """Тестирует статический инструмент с init_params"""
    print("🧪 Тестируем статический инструмент с init_params...")
    
    agent_config = {
        "name": "Weather Agent",
        "agent_id": "weather_test_agent",
        "description": "Агент для тестирования погодных инструментов",
        "instructions": "Ты помощник по погоде. Используй инструменты для получения информации о погоде.",
        "tools_config": [
            {
                "type": "static",
                "import_path": "agents.tools.weather_toolkit.WeatherToolkit",
                "init_params": {
                    "api_key": "test_api_key_123",
                    "units": "metric",
                    "lang": "ru"
                }
            },
            {
                "type": "static",
                "import_path": "agents.tools.weather_toolkit.SimpleCalculatorToolkit",
                "init_params": {
                    "precision": 3
                }
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/dynamic-agents/", json=agent_config)
        if response.status_code == 201:
            print("✅ Агент с init_params создан успешно")
            return response.json()
        else:
            print(f"❌ Ошибка создания агента: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_mcp_tool_config():
    """Тестирует MCP инструмент"""
    print("🧪 Тестируем MCP инструмент...")
    
    agent_config = {
        "name": "MCP Weather Agent",
        "agent_id": "mcp_weather_test_agent",
        "description": "Агент с MCP сервером погоды",
        "instructions": "Ты помощник с доступом к MCP серверу погоды.",
        "tools_config": [
            {
                "type": "mcp",
                "transport": "stdio",
                "command": "python examples/weather_mcp_server.py",
                "env": {
                    "WEATHER_API_KEY": "demo_key_for_testing"
                },
                "include_tools": ["get_weather", "get_forecast", "get_uv_index"]
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/dynamic-agents/", json=agent_config)
        if response.status_code == 201:
            print("✅ Агент с MCP создан успешно")
            return response.json()
        else:
            print(f"❌ Ошибка создания MCP агента: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_dynamic_tool():
    """Тестирует создание динамического инструмента"""
    print("🧪 Тестируем динамический инструмент...")
    
    tool_config = {
        "name": "Конвертер валют",
        "tool_id": "currency_converter_v1",
        "description": "Конвертирует валюты по курсу",
        "function_name": "convert_currency",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Сумма для конвертации"
                },
                "from_currency": {
                    "type": "string",
                    "description": "Исходная валюта (USD, EUR, RUB)"
                },
                "to_currency": {
                    "type": "string", 
                    "description": "Целевая валюта (USD, EUR, RUB)"
                }
            },
            "required": ["amount", "from_currency", "to_currency"]
        },
        "implementation": """
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    # Демо курсы валют
    rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'RUB': 90.0,
        'GBP': 0.75
    }
    
    try:
        if from_currency not in rates or to_currency not in rates:
            return f"❌ Неподдерживаемая валюта. Доступны: {', '.join(rates.keys())}"
        
        # Конвертируем через USD как базовую валюту
        usd_amount = amount / rates[from_currency]
        result = usd_amount * rates[to_currency]
        
        return f"💱 {amount} {from_currency} = {result:.2f} {to_currency}"
        
    except Exception as e:
        return f"❌ Ошибка конвертации: {e}"
"""
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/dynamic-tools/", json=tool_config)
        if response.status_code == 201:
            print("✅ Динамический инструмент создан успешно")
            return response.json()
        else:
            print(f"❌ Ошибка создания динамического инструмента: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_combined_agent():
    """Тестирует агента со всеми типами инструментов"""
    print("🧪 Тестируем комбинированного агента...")
    
    agent_config = {
        "name": "Universal Assistant",
        "agent_id": "universal_test_agent",
        "description": "Универсальный помощник со всеми типами инструментов",
        "instructions": """
        Ты универсальный помощник с доступом к различным инструментам:
        1. Погодные данные (статический инструмент с API ключом)
        2. Калькулятор (статический инструмент)
        3. Конвертер валют (динамический инструмент)
        4. MCP сервер погоды (внешний сервер)
        
        Используй подходящие инструменты для каждого запроса.
        """,
        "tools_config": [
            # Статический инструмент с init_params
            {
                "type": "static",
                "import_path": "agents.tools.weather_toolkit.WeatherToolkit",
                "init_params": {
                    "api_key": "test_key_123",
                    "units": "metric"
                }
            },
            # Статический калькулятор
            {
                "type": "static",
                "import_path": "agents.tools.weather_toolkit.SimpleCalculatorToolkit",
                "init_params": {
                    "precision": 2
                }
            },
            # Динамический инструмент
            {
                "type": "dynamic",
                "tool_id": "currency_converter_v1"
            },
            # MCP сервер
            {
                "type": "mcp",
                "transport": "stdio",
                "command": "python examples/weather_mcp_server.py",
                "env": {
                    "WEATHER_API_KEY": "mcp_demo_key"
                },
                "include_tools": ["get_weather", "calculate_wind_chill"]
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/dynamic-agents/", json=agent_config)
        if response.status_code == 201:
            print("✅ Комбинированный агент создан успешно")
            return response.json()
        else:
            print(f"❌ Ошибка создания комбинированного агента: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_agent_chat(agent_id: str, message: str):
    """Тестирует чат с агентом"""
    print(f"💬 Тестируем чат с агентом {agent_id}...")
    
    chat_data = {
        "message": message,
        "user_id": "test_user",
        "session_id": "test_session"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/agents/{agent_id}/chat", json=chat_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ответ агента: {result.get('content', 'Нет ответа')}")
            return result
        else:
            print(f"❌ Ошибка чата: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования кастомных инструментов\n")
    
    # 1. Тест динамического инструмента
    print("=" * 50)
    dynamic_tool = test_dynamic_tool()
    
    # 2. Тест статического инструмента с init_params
    print("\n" + "=" * 50)
    weather_agent = test_static_tool_with_init_params()
    
    # 3. Тест MCP инструмента
    print("\n" + "=" * 50)
    mcp_agent = test_mcp_tool_config()
    
    # 4. Тест комбинированного агента
    print("\n" + "=" * 50)
    universal_agent = test_combined_agent()
    
    # 5. Тестируем чат если агенты созданы
    print("\n" + "=" * 50)
    if weather_agent:
        test_agent_chat(weather_agent['agent_id'], "Какая погода в Москве?")
    
    if universal_agent:
        print("\n" + "-" * 30)
        test_agent_chat(universal_agent['agent_id'], "Конвертируй 100 USD в EUR")
        
        print("\n" + "-" * 30)
        test_agent_chat(universal_agent['agent_id'], "Вычисли 15 * 23 + 45")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    main() 