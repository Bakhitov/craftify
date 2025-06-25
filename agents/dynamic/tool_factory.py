"""
Фабрика для создания динамических инструментов из конфигурации в БД.
Использует стандартные классы agno без модификации.
"""
import ast
import json
import re
from typing import Optional, Dict, Any, List, Callable, Set
from sqlalchemy import text

from agno.tools.function import Function
from db.session import SessionLocal


class DynamicToolFactory:
    """
    Фабрика для создания динамических инструментов из БД.
    Использует только стандартные классы agno для максимальной совместимости.
    """
    
    # Список опасных функций и модулей
    DANGEROUS_FUNCTIONS = {
        'exec', 'eval', 'compile', 'open', 'file',
        'input', 'raw_input', 'reload', 'delattr', 'setattr',
        'getattr', 'hasattr', 'globals', 'locals', 'vars',
        'dir', 'help', 'exit', 'quit'
    }
    
    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'tempfile',
        'pickle', 'shelve', 'marshal', 'imp', 'importlib',
        'socket', 'urllib', 'requests', 'http'
    }
    
    # Разрешенные встроенные функции
    SAFE_BUILTINS = {
        'print', 'len', 'str', 'int', 'float', 'bool',
        'list', 'dict', 'tuple', 'set', 'range',
        'enumerate', 'zip', 'sum', 'min', 'max',
        'abs', 'round', 'pow', 'divmod',
        'Exception', 'ValueError', 'TypeError', 'AttributeError',
        '__import__'
    }
    
    # Разрешенные модули
    SAFE_MODULES = {
        'math', 'json', 're', 'datetime', 'random',
        'string', 'itertools', 'functools', 'operator'
    }
    
    @staticmethod
    def create_tool_from_db(tool_id: str) -> Optional[Function]:
        """
        Создает инструмент из конфигурации в БД используя стандартный класс agno.Function.
        
        Args:
            tool_id: ID инструмента в БД
            
        Returns:
            Экземпляр Function или None если инструмент не найден
        """
        try:
            # Получаем конфигурацию инструмента из БД
            tool_config = DynamicToolFactory._get_tool_config(tool_id)
            if not tool_config:
                return None
            
            # Валидируем код на безопасность
            validation_result = DynamicToolFactory._validate_code_security(
                tool_config['implementation']
            )
            if not validation_result['is_safe']:
                print(f"Небезопасный код в инструменте {tool_id}: {validation_result['reason']}")
                return None
            
            # Создаем функцию из кода в БД
            entrypoint = DynamicToolFactory._create_function_from_code(
                tool_config['implementation'],
                tool_config['function_name']
            )
            
            if not entrypoint:
                return None
            
            # Создаем безопасное имя для OpenAI API (только буквы, цифры, подчеркивания и дефисы)
            safe_function_name = DynamicToolFactory._create_safe_function_name(
                tool_config['function_name'], 
                tool_config['tool_id']
            )
            
            # Создаем инструмент используя стандартный класс agno.Function
            function = Function(
                name=safe_function_name,  # Используем безопасное имя вместо русского названия
                description=tool_config.get('description'),
                parameters=tool_config.get('parameters_schema', {}),
                entrypoint=entrypoint,
                skip_entrypoint_processing=False  # Позволяем agno обработать функцию
            )
            
            return function
            
        except Exception as e:
            print(f"Ошибка при создании динамического инструмента {tool_id}: {e}")
            return None
    
    @staticmethod
    def _validate_code_security(code: str) -> Dict[str, Any]:
        """
        Валидирует код на предмет безопасности.
        
        Args:
            code: Python код для проверки
            
        Returns:
            Словарь с результатом валидации
        """
        try:
            # Парсим код в AST
            tree = ast.parse(code)
            
            # Ищем опасные конструкции
            dangerous_nodes = []
            
            for node in ast.walk(tree):
                # Проверяем вызовы функций
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in DynamicToolFactory.DANGEROUS_FUNCTIONS:
                            dangerous_nodes.append(f"Опасная функция: {func_name}")
                
                # Проверяем импорты
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in DynamicToolFactory.DANGEROUS_MODULES:
                            dangerous_nodes.append(f"Опасный модуль: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in DynamicToolFactory.DANGEROUS_MODULES:
                        dangerous_nodes.append(f"Опасный модуль: {node.module}")
                
                # Проверяем доступ к атрибутам
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == '__builtins__':
                            dangerous_nodes.append("Доступ к __builtins__")
            
            if dangerous_nodes:
                return {
                    'is_safe': False,
                    'reason': '; '.join(dangerous_nodes)
                }
            
            return {
                'is_safe': True,
                'reason': 'Код прошел проверку безопасности'
            }
            
        except SyntaxError as e:
            return {
                'is_safe': False,
                'reason': f'Синтаксическая ошибка: {e}'
            }
        except Exception as e:
            return {
                'is_safe': False,
                'reason': f'Ошибка валидации: {e}'
            }
    
    @staticmethod
    def _create_safe_function_name(function_name: str, tool_id: str) -> str:
        """
        Создает безопасное имя функции для OpenAI API.
        
        Args:
            function_name: Исходное имя функции
            tool_id: ID инструмента как fallback
            
        Returns:
            Безопасное имя функции (только a-zA-Z0-9_-)
        """
        # Сначала пробуем использовать function_name если он уже безопасный
        if re.match(r'^[a-zA-Z0-9_-]+$', function_name):
            return function_name
        
        # Если function_name содержит недопустимые символы, используем tool_id
        # Заменяем недопустимые символы на подчеркивания
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', tool_id)
        
        # Убираем множественные подчеркивания
        safe_name = re.sub(r'_{2,}', '_', safe_name)
        
        # Убираем подчеркивания в начале и конце
        safe_name = safe_name.strip('_')
        
        # Если результат пустой, используем fallback
        if not safe_name:
            safe_name = 'dynamic_tool'
        
        return safe_name
    
    @staticmethod
    def _get_tool_config(tool_id: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию инструмента из БД"""
        with SessionLocal() as session:
            try:
                query = text("""
                    SELECT name, tool_id, description, function_name,
                           parameters_schema, implementation
                    FROM dynamic_tools 
                    WHERE tool_id = :tool_id AND is_active = true
                """)
                
                result = session.execute(query, {"tool_id": tool_id})
                row = result.fetchone()
                
                if row:
                    return {
                        "name": row.name,
                        "tool_id": row.tool_id,
                        "description": row.description,
                        "function_name": row.function_name,
                        "parameters_schema": row.parameters_schema or {},
                        "implementation": row.implementation
                    }
                
                return None
                
            except Exception as e:
                print(f"Ошибка при получении конфигурации инструмента {tool_id}: {e}")
                return None
    
    @staticmethod
    def _create_function_from_code(code: str, function_name: str) -> Optional[Callable]:
        """
        Создает исполняемую функцию из Python кода с улучшенной безопасностью.
        
        Args:
            code: Python код функции
            function_name: Имя функции
            
        Returns:
            Исполняемая функция или None в случае ошибки
        """
        try:
            # Создаем локальное пространство имен для выполнения кода
            local_namespace = {}
            
            # Импортируем только разрешенные модули
            safe_modules = {}
            for module_name in DynamicToolFactory.SAFE_MODULES:
                try:
                    safe_modules[module_name] = __import__(module_name)
                except ImportError:
                    pass  # Модуль недоступен
            
            # Создаем ограниченное пространство имен
            safe_builtins = {}
            
            # __builtins__ может быть словарем или модулем
            builtins_source = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
            
            for func_name in DynamicToolFactory.SAFE_BUILTINS:
                if func_name in builtins_source:
                    safe_builtins[func_name] = builtins_source[func_name]
            
            global_namespace = {
                '__builtins__': safe_builtins,
                **safe_modules
            }
            
            # Выполняем код в контролируемом пространстве имен
            exec(code, global_namespace, local_namespace)
            
            # Получаем функцию из локального пространства имен
            if function_name in local_namespace:
                return local_namespace[function_name]
            else:
                print(f"Функция {function_name} не найдена в коде")
                return None
                
        except Exception as e:
            print(f"Ошибка при создании функции из кода: {e}")
            return None
    
    @staticmethod
    def get_dynamic_tool_ids() -> List[str]:
        """Получает список ID всех активных динамических инструментов"""
        with SessionLocal() as session:
            try:
                query = text("""
                    SELECT tool_id 
                    FROM dynamic_tools 
                    WHERE is_active = true 
                    ORDER BY tool_id
                """)
                
                result = session.execute(query)
                return [row.tool_id for row in result.fetchall()]
                
            except Exception as e:
                print(f"Ошибка при получении списка динамических инструментов: {e}")
                return []
    
    @staticmethod
    def validate_tool_code(code: str, function_name: str) -> Dict[str, Any]:
        """
        Валидирует код инструмента перед сохранением в БД.
        
        Args:
            code: Python код функции
            function_name: Имя функции
            
        Returns:
            Словарь с результатом валидации
        """
        try:
            # Проверяем безопасность кода
            security_result = DynamicToolFactory._validate_code_security(code)
            if not security_result['is_safe']:
                return {
                    "valid": False,
                    "error": f"Небезопасный код: {security_result['reason']}"
                }
            
            # Проверяем синтаксис
            compile(code, '<string>', 'exec')
            
            # Проверяем что функция создается корректно
            test_function = DynamicToolFactory._create_function_from_code(code, function_name)
            if not test_function:
                return {
                    "valid": False,
                    "error": f"Функция {function_name} не найдена в коде"
                }
            
            # Проверяем что функция вызываема
            if not callable(test_function):
                return {
                    "valid": False,
                    "error": f"{function_name} не является вызываемой функцией"
                }
            
            return {
                "valid": True,
                "message": "Код инструмента валиден и безопасен"
            }
            
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"Синтаксическая ошибка: {e}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Ошибка валидации: {e}"
            } 