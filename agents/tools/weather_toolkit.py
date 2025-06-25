"""
Пример инструментов для тестирования init_params в динамических агентах.
Демонстрирует создание статических инструментов с параметрами инициализации.
"""

import json
import requests
from typing import Optional, Dict, Any
from agno.tools.toolkit import Toolkit


class WeatherToolkit(Toolkit):
    """
    Инструмент для работы с погодой с поддержкой init_params.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        units: str = "metric",
        lang: str = "ru"
    ):
        super().__init__(name="WeatherToolkit")
        self.api_key = api_key
        self.units = units
        self.lang = lang
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # Регистрируем инструменты
        self.register(self.get_weather)
        self.register(self.get_forecast)
        self.register(self.get_weather_alerts)
    
    def get_weather(self, city: str) -> str:
        """
        Получает текущую погоду в указанном городе.
        
        Args:
            city: Название города
            
        Returns:
            Описание текущей погоды
        """
        try:
            if not self.api_key:
                return f"🌤️ Демо погода для {city}: Солнечно, +25°C (единицы: {self.units}, язык: {self.lang})"
            
            # Здесь был бы реальный API запрос с использованием self.api_key
            return f"🌤️ Погода в {city}: Солнечно, +25°C (API ключ: {self.api_key[:8]}..., единицы: {self.units})"
            
        except Exception as e:
            return f"❌ Ошибка получения погоды: {e}"
    
    def get_forecast(self, city: str, days: int = 3) -> str:
        """
        Получает прогноз погоды на несколько дней.
        
        Args:
            city: Название города
            days: Количество дней прогноза (1-7)
            
        Returns:
            Прогноз погоды
        """
        if days < 1 or days > 7:
            return "❌ Количество дней должно быть от 1 до 7"
        
        try:
            forecast = []
            for day in range(days):
                temp = 20 + day if self.units == "metric" else 68 + day * 2
                unit = "°C" if self.units == "metric" else "°F"
                forecast.append(f"День {day+1}: +{temp}{unit}")
            
            source = f"с API ключом ({self.api_key[:8]}...)" if self.api_key else "демо режим"
            return f"🔮 Прогноз для {city} на {days} дней ({source}):\n" + "\n".join(forecast)
            
        except Exception as e:
            return f"❌ Ошибка получения прогноза: {e}"
    
    def get_weather_alerts(self, city: str, country_code: Optional[str] = None) -> str:
        """
        Получает погодные предупреждения для указанного города.
        
        Args:
            city: Название города
            country_code: Код страны (опционально)
            
        Returns:
            Информация о погодных предупреждениях
        """
        try:
            if not self.api_key:
                # Демо режим
                return f"🔔 Демо: Для {city} активных погодных предупреждений нет"
            
            # Сначала получаем координаты города
            location = f"{city},{country_code}" if country_code else city
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
            
            geo_params = {
                "q": location,
                "limit": 1,
                "appid": self.api_key
            }
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            geo_response.raise_for_status()
            
            geo_data = geo_response.json()
            if not geo_data:
                return f"❌ Город {city} не найден"
            
            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
            
            # Получаем данные о предупреждениях
            alerts_url = f"{self.base_url}/onecall"
            
            alerts_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "exclude": "minutely,hourly,daily",
                "lang": self.lang
            }
            
            alerts_response = requests.get(alerts_url, params=alerts_params, timeout=10)
            alerts_response.raise_for_status()
            
            alerts_data = alerts_response.json()
            
            if "alerts" not in alerts_data or not alerts_data["alerts"]:
                return f"🔔 Для {city} активных погодных предупреждений нет"
            
            # Форматируем предупреждения
            result = f"⚠️ Погодные предупреждения для {city}:\n\n"
            
            for alert in alerts_data["alerts"]:
                sender = alert.get("sender_name", "Неизвестно")
                event = alert.get("event", "Неизвестное событие")
                description = alert.get("description", "Описание отсутствует")
                
                result += f"🚨 {event} (от {sender})\n"
                result += f"📝 {description}\n\n"
            
            return result
            
        except requests.exceptions.RequestException as e:
            return f"❌ Ошибка сети при получении предупреждений: {e}"
        except KeyError as e:
            return f"❌ Ошибка обработки данных предупреждений: {e}"
        except Exception as e:
            return f"❌ Ошибка получения предупреждений: {e}"


class SimpleCalculatorToolkit(Toolkit):
    """
    Простой калькулятор с настраиваемой точностью.
    """
    
    def __init__(self, precision: int = 2):
        super().__init__(name="SimpleCalculatorToolkit")
        self.precision = precision
    
    def calculate(self, expression: str) -> str:
        """
        Выполняет математическое вычисление.
        
        Args:
            expression: Математическое выражение
            
        Returns:
            Результат вычисления
        """
        try:
            # Безопасное вычисление только математических выражений
            result = self._safe_eval(expression)
            
            # Применяем настраиваемую точность
            if isinstance(result, float):
                result = round(result, self.precision)
            
            return f"🔢 {expression} = {result} (точность: {self.precision} знаков)"
            
        except ZeroDivisionError:
            return "❌ Ошибка: деление на ноль"
        except Exception as e:
            return f"❌ Ошибка вычисления: {e}"
    
    def _safe_eval(self, expression: str) -> float:
        """
        Безопасное вычисление математических выражений без eval.
        
        Args:
            expression: Математическое выражение
            
        Returns:
            Результат вычисления
        """
        import ast
        import operator
        
        # Разрешенные операции
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        def _eval(node):
            if isinstance(node, ast.Constant):  # Python 3.8+
                return node.value
            elif isinstance(node, ast.Num):  # Python < 3.8
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](_eval(node.operand))
            else:
                raise ValueError(f"Неподдерживаемая операция: {type(node)}")
        
        # Парсим выражение
        try:
            tree = ast.parse(expression, mode='eval')
            return _eval(tree.body)
        except (SyntaxError, ValueError, KeyError) as e:
            raise ValueError(f"Недопустимое выражение: {e}")
    
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> str:
        """
        Конвертирует единицы измерения.
        
        Args:
            value: Значение для конвертации
            from_unit: Исходная единица (celsius, fahrenheit, meters, feet)
            to_unit: Целевая единица
            
        Returns:
            Результат конвертации
        """
        try:
            conversions = {
                ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
                ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
                ("meters", "feet"): lambda x: x * 3.28084,
                ("feet", "meters"): lambda x: x / 3.28084,
            }
            
            key = (from_unit.lower(), to_unit.lower())
            if key not in conversions:
                return f"❌ Конвертация {from_unit} -> {to_unit} не поддерживается"
            
            result = conversions[key](value)
            result = round(result, self.precision)
            
            return f"🔄 {value} {from_unit} = {result} {to_unit} (точность: {self.precision})"
            
        except Exception as e:
            return f"❌ Ошибка конвертации: {e}"


class ConfigurableTextToolkit(Toolkit):
    """
    Инструмент для работы с текстом с настраиваемыми параметрами.
    """
    
    def __init__(
        self,
        max_length: int = 1000,
        default_language: str = "ru",
        case_sensitive: bool = False
    ):
        super().__init__(name="ConfigurableTextToolkit")
        self.max_length = max_length
        self.default_language = default_language
        self.case_sensitive = case_sensitive
    
    def analyze_text(self, text: str) -> str:
        """
        Анализирует текст с учетом настроек.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Результат анализа
        """
        try:
            if len(text) > self.max_length:
                text = text[:self.max_length] + "..."
            
            # Анализ с учетом регистра
            analysis_text = text if self.case_sensitive else text.lower()
            
            word_count = len(analysis_text.split())
            char_count = len(analysis_text)
            
            return f"""📊 Анализ текста (язык: {self.default_language}, регистр: {'важен' if self.case_sensitive else 'не важен'}):
- Слов: {word_count}
- Символов: {char_count}
- Максимальная длина: {self.max_length}
- Обрезан: {'да' if len(text) > self.max_length else 'нет'}"""
            
        except Exception as e:
            return f"❌ Ошибка анализа текста: {e}"
    
    def format_text(self, text: str, style: str = "title") -> str:
        """
        Форматирует текст в заданном стиле.
        
        Args:
            text: Исходный текст
            style: Стиль форматирования (title, upper, lower, sentence)
            
        Returns:
            Отформатированный текст
        """
        try:
            if len(text) > self.max_length:
                text = text[:self.max_length]
            
            styles = {
                "title": text.title(),
                "upper": text.upper(),
                "lower": text.lower(),
                "sentence": text.capitalize()
            }
            
            if style not in styles:
                return f"❌ Неподдерживаемый стиль: {style}. Доступны: {', '.join(styles.keys())}"
            
            result = styles[style]
            
            return f"✨ Форматирование ({style}, язык: {self.default_language}):\n{result}"
            
        except Exception as e:
            return f"❌ Ошибка форматирования: {e}" 