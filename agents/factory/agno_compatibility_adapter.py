"""
Адаптер совместимости с различными версиями Agno.
Обеспечивает нативную интеграцию и автоматическую адаптацию к изменениям в Agno.
"""
import inspect
from typing import Dict, Any, Optional, List, Union, get_type_hints
from agno.agent import Agent
from agno.models.base import Model
from agno.tools.function import Function
from agno.tools.toolkit import Toolkit


class AgnoCompatibilityAdapter:
    """
    Адаптер для обеспечения совместимости с различными версиями Agno.
    Автоматически определяет доступные параметры и функции.
    """
    
    def __init__(self):
        self._agent_signature = None
        self._supported_params = None
        self._agno_version = None
        self._initialize_compatibility()
    
    def _initialize_compatibility(self):
        """Инициализирует информацию о совместимости с текущей версией Agno"""
        try:
            # Получаем сигнатуру конструктора Agent
            self._agent_signature = inspect.signature(Agent.__init__)
            self._supported_params = set(self._agent_signature.parameters.keys())
            
            # Определяем версию Agno (если возможно)
            try:
                import agno
                self._agno_version = getattr(agno, '__version__', 'unknown')
            except:
                self._agno_version = 'unknown'
                
        except Exception as e:
            print(f"Ошибка при инициализации адаптера совместимости: {e}")
            self._supported_params = set()
    
    def filter_agent_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Фильтрует параметры для конструктора Agent, оставляя только поддерживаемые.
        
        Args:
            params: Словарь параметров для Agent
            
        Returns:
            Отфильтрованный словарь параметров
        """
        if not self._supported_params:
            return params
        
        # Оставляем только параметры, поддерживаемые текущей версией Agno
        filtered_params = {
            key: value for key, value in params.items() 
            if key in self._supported_params
        }
        
        # Логируем отфильтрованные параметры для отладки
        filtered_out = set(params.keys()) - set(filtered_params.keys())
        if filtered_out:
            print(f"Отфильтрованы неподдерживаемые параметры Agent: {filtered_out}")
        
        return filtered_params
    
    def create_agent_safely(self, **params) -> Optional[Agent]:
        """
        Безопасно создает агента с автоматической фильтрацией параметров.
        
        Args:
            **params: Параметры для создания агента
            
        Returns:
            Экземпляр Agent или None при ошибке
        """
        try:
            # Фильтруем параметры
            filtered_params = self.filter_agent_params(params)
            
            # Создаем агента
            return Agent(**filtered_params)
            
        except Exception as e:
            print(f"Ошибка при создании агента: {e}")
            
            # Пытаемся создать базового агента с минимальными параметрами
            try:
                basic_params = {
                    key: value for key, value in params.items()
                    if key in ['model', 'name', 'agent_id', 'user_id', 'session_id']
                }
                basic_params = self.filter_agent_params(basic_params)
                return Agent(**basic_params)
            except Exception as fallback_error:
                print(f"Не удалось создать даже базового агента: {fallback_error}")
                return None
    
    def is_parameter_supported(self, param_name: str) -> bool:
        """Проверяет поддерживается ли параметр в текущей версии Agno"""
        return param_name in self._supported_params if self._supported_params else False
    
    def get_supported_parameters(self) -> List[str]:
        """Возвращает список поддерживаемых параметров Agent"""
        return list(self._supported_params) if self._supported_params else []
    
    def get_agno_version(self) -> str:
        """Возвращает версию Agno"""
        return self._agno_version or 'unknown'
    
    def validate_tool_compatibility(self, tool: Union[Function, Toolkit, Dict]) -> bool:
        """
        Проверяет совместимость инструмента с текущей версией Agno.
        
        Args:
            tool: Инструмент для проверки
            
        Returns:
            True если инструмент совместим
        """
        try:
            if isinstance(tool, (Function, Toolkit)):
                return True
            elif isinstance(tool, dict):
                # Проверяем базовую структуру словаря-инструмента
                return 'name' in tool or 'function' in tool
            else:
                # Проверяем что это callable
                return callable(tool)
        except:
            return False
    
    def adapt_model_params(self, model_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Адаптирует параметры модели под текущую версию Agno.
        
        Args:
            model_type: Тип модели (openai, anthropic, etc.)
            params: Параметры модели
            
        Returns:
            Адаптированные параметры
        """
        # Базовые параметры, поддерживаемые большинством моделей
        common_params = {
            'id', 'temperature', 'max_tokens', 'top_p', 
            'frequency_penalty', 'presence_penalty'
        }
        
        # Фильтруем только известные параметры
        adapted_params = {
            key: value for key, value in params.items()
            if key in common_params and value is not None
        }
        
        return adapted_params
    
    def get_compatibility_info(self) -> Dict[str, Any]:
        """Возвращает информацию о совместимости"""
        return {
            'agno_version': self._agno_version,
            'supported_params_count': len(self._supported_params) if self._supported_params else 0,
            'supported_params': list(self._supported_params) if self._supported_params else [],
            'has_store_events': self.is_parameter_supported('store_events'),
            'has_session_state': self.is_parameter_supported('session_state'),
            'has_extra_data': self.is_parameter_supported('extra_data'),
            'has_team_support': self.is_parameter_supported('team'),
            'has_memory_v2': self.is_parameter_supported('memory'),
        }


# Глобальный экземпляр адаптера
agno_adapter = AgnoCompatibilityAdapter() 