#!/usr/bin/env python3
"""
Пример MCP сервера для работы с погодой.
Демонстрирует создание MCP сервера для использования в динамических агентах.

Запуск:
    python examples/weather_mcp_server.py

Использование в агенте:
    {
        "type": "mcp",
        "transport": "stdio", 
        "command": "python examples/weather_mcp_server.py",
        "env": {"WEATHER_API_KEY": "your_api_key_here"},
        "include_tools": ["get_weather", "get_forecast"]
    }
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP не установлен. Установите используя: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Создаем MCP сервер
server = Server("weather-mcp-server")


@server.tool()
async def get_weather(location: str) -> str:
    """
    Получает текущую погоду для указанного места.
    
    Args:
        location: Название города или координаты
        
    Returns:
        Описание текущей погоды
    """
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        
        # Симуляция API запроса
        await asyncio.sleep(0.1)  # Имитация сетевого запроса
        
        if not api_key:
            return f"🌤️ Демо: Солнечно, +25°C в {location}. Влажность: 65%, Ветер: 3 м/с (MCP сервер)"
        
        # Здесь был бы реальный API запрос к OpenWeatherMap
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}") as resp:
        #         data = await resp.json()
        #         return format_weather_data(data)
        
        return f"🌤️ Погода в {location}: солнечно, +25°C, влажность 65% (MCP с API ключом)"
        
    except Exception as e:
        return f"❌ Ошибка получения погоды: {e}"


@server.tool()
async def get_forecast(location: str, days: int = 3) -> str:
    """
    Получает прогноз погоды на несколько дней.
    
    Args:
        location: Название города или координаты
        days: Количество дней прогноза (1-5)
        
    Returns:
        Прогноз погоды
    """
    try:
        if days < 1 or days > 5:
            return "❌ Количество дней должно быть от 1 до 5"
        
        await asyncio.sleep(0.2)  # Имитация сетевого запроса
        
        api_key = os.getenv("WEATHER_API_KEY")
        
        forecast = []
        for day in range(days):
            temp = 22 + day
            weather_types = ["солнечно", "облачно", "дождь", "переменная облачность"]
            weather = weather_types[day % len(weather_types)]
            forecast.append(f"📅 День {day+1}: {weather}, +{temp}°C")
        
        source = "с API ключом" if api_key else "демо режим"
        return f"🔮 Прогноз для {location} на {days} дней ({source}):\n" + "\n".join(forecast)
        
    except Exception as e:
        return f"❌ Ошибка получения прогноза: {e}"


@server.tool()
async def get_weather_alerts(location: str) -> str:
    """
    Получает погодные предупреждения для указанного места.
    
    Args:
        location: Название города или координаты
        
    Returns:
        Информация о погодных предупреждениях
    """
    try:
        await asyncio.sleep(0.1)
        
        # Симуляция проверки предупреждений
        import random
        
        if random.random() < 0.3:  # 30% шанс предупреждения
            alerts = [
                "🌪️ Предупреждение о сильном ветре (до 20 м/с)",
                "🌧️ Предупреждение о сильных дождях",
                "❄️ Предупреждение о снегопаде",
                "🌡️ Предупреждение о резком похолодании"
            ]
            alert = random.choice(alerts)
            return f"⚠️ Погодное предупреждение для {location}:\n{alert}"
        else:
            return f"🔔 Для {location} активных погодных предупреждений нет"
            
    except Exception as e:
        return f"❌ Ошибка получения предупреждений: {e}"


@server.tool()
async def calculate_wind_chill(temperature: float, wind_speed: float) -> str:
    """
    Вычисляет ощущаемую температуру с учетом ветра.
    
    Args:
        temperature: Температура в градусах Цельсия
        wind_speed: Скорость ветра в м/с
        
    Returns:
        Ощущаемая температура
    """
    try:
        # Формула расчета wind chill (упрощенная)
        if wind_speed > 1.34:  # Минимальная скорость ветра для расчета
            # Конвертируем в км/ч для формулы
            wind_kmh = wind_speed * 3.6
            
            wind_chill = 13.12 + 0.6215 * temperature - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temperature * (wind_kmh ** 0.16)
            
            return f"🌡️ При температуре {temperature}°C и ветре {wind_speed} м/с ощущается как {wind_chill:.1f}°C"
        else:
            return f"🌡️ При слабом ветре ({wind_speed} м/с) ощущается как {temperature}°C"
            
    except Exception as e:
        return f"❌ Ошибка расчета ощущаемой температуры: {e}"


@server.tool() 
async def get_uv_index(location: str) -> str:
    """
    Получает UV индекс для указанного места.
    
    Args:
        location: Название города или координаты
        
    Returns:
        Информация об UV индексе
    """
    try:
        await asyncio.sleep(0.1)
        
        # Симуляция получения UV индекса
        import random
        uv_index = random.randint(1, 11)
        
        uv_levels = {
            (1, 2): ("низкий", "🟢"),
            (3, 5): ("умеренный", "🟡"), 
            (6, 7): ("высокий", "🟠"),
            (8, 10): ("очень высокий", "🔴"),
            (11, 15): ("экстремальный", "🟣")
        }
        
        level = "неизвестный"
        color = "⚪"
        
        for (min_uv, max_uv), (level_name, level_color) in uv_levels.items():
            if min_uv <= uv_index <= max_uv:
                level = level_name
                color = level_color
                break
        
        return f"☀️ UV индекс в {location}: {uv_index} ({level}) {color}"
        
    except Exception as e:
        return f"❌ Ошибка получения UV индекса: {e}"


async def main():
    """Запускает MCP сервер"""
    try:
        await server.run()
    except KeyboardInterrupt:
        print("\n🛑 MCP сервер остановлен", file=sys.stderr)
    except Exception as e:
        print(f"❌ Ошибка MCP сервера: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Запуск Weather MCP сервера...", file=sys.stderr)
    print("🔧 Доступные инструменты: get_weather, get_forecast, get_weather_alerts, calculate_wind_chill, get_uv_index", file=sys.stderr)
    
    # Проверяем наличие API ключа
    api_key = os.getenv("WEATHER_API_KEY")
    if api_key:
        print(f"🔑 Используется API ключ: {api_key[:8]}...", file=sys.stderr)
    else:
        print("⚠️ API ключ не найден, работаем в демо режиме", file=sys.stderr)
    
    asyncio.run(main()) 