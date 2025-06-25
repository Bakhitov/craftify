"""
Изолированная фабрика для создания агентов.
Обеспечивает совместимость между статическими и динамическими агентами.
"""
from typing import Optional, Dict, Any
from agno.agent import Agent

from agents.dynamic.agent_factory import DynamicAgentFactory
from agents.factory.agno_compatibility_adapter import agno_adapter


class IsolatedAgentFactory:
    """
    Изолированная фабрика для создания агентов.
    Обеспечивает единый интерфейс для создания статических и динамических агентов.
    """
    
    @staticmethod
    def create_agent(
        agent_type: str,
        agent_id: str,
        **kwargs
    ) -> Optional[Agent]:
        """
        Создает агента по типу и ID.
        
        Args:
            agent_type: Тип агента ('static' или 'dynamic')
            agent_id: ID агента
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр Agent или None
        """
        try:
            if agent_type == 'dynamic':
                return DynamicAgentFactory.create_agent_from_db(
                    agent_id=agent_id,
                    **kwargs
                )
            elif agent_type == 'static':
                return IsolatedAgentFactory._create_static_agent(
                    agent_id=agent_id,
                    **kwargs
                )
            else:
                print(f"Неизвестный тип агента: {agent_type}")
                return None
                
        except Exception as e:
            print(f"Ошибка при создании агента {agent_id}: {e}")
            return None
    
    @staticmethod
    def _create_static_agent(agent_id: str, **kwargs) -> Optional[Agent]:
        """
        Создает статического агента.
        
        Args:
            agent_id: ID статического агента
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр Agent или None
        """
        # Импортируем статических агентов
        try:
            if agent_id == 'agno_assist':
                from agents.static.agno_assist import AgnoAssist
                agent_class = AgnoAssist()
                return agent_class.get_agent()
            elif agent_id == 'finance_agent':
                from agents.static.finance_agent import FinanceAgent
                agent_class = FinanceAgent()
                return agent_class.get_agent()
            elif agent_id == 'web_agent':
                from agents.static.web_agent import WebAgent
                agent_class = WebAgent()
                return agent_class.get_agent()
            else:
                print(f"Неизвестный статический агент: {agent_id}")
                return None
                
        except ImportError as e:
            print(f"Ошибка импорта статического агента {agent_id}: {e}")
            return None
        except Exception as e:
            print(f"Ошибка создания статического агента {agent_id}: {e}")
            return None
    
    @staticmethod
    def get_available_agents() -> Dict[str, Any]:
        """
        Возвращает информацию о доступных агентах.
        
        Returns:
            Словарь с информацией об агентах
        """
        agents_info = {
            'static': {
                'agno_assist': {
                    'name': 'Agno Assistant',
                    'description': 'Помощник по работе с Agno фреймворком',
                    'available': True
                },
                'finance_agent': {
                    'name': 'Finance Agent',
                    'description': 'Агент для финансовых операций',
                    'available': True
                },
                'web_agent': {
                    'name': 'Web Agent',
                    'description': 'Агент для работы с веб-ресурсами',
                    'available': True
                }
            },
            'dynamic': []
        }
        
        # Получаем динамических агентов из БД
        try:
            dynamic_agent_ids = DynamicAgentFactory.get_dynamic_agent_ids()
            agents_info['dynamic'] = [
                {
                    'agent_id': agent_id,
                    'type': 'dynamic',
                    'available': True
                }
                for agent_id in dynamic_agent_ids
            ]
        except Exception as e:
            print(f"Ошибка получения динамических агентов: {e}")
        
        return agents_info 