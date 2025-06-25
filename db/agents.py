from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import SessionLocal


def get_agent_from_db(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные агента из таблицы agents по agent_id.
    
    Args:
        agent_id: ID агента для поиска
        
    Returns:
        Словарь с данными агента или None если агент не найден
    """
    with SessionLocal() as session:
        try:
            # Выполняем запрос к таблице agents
            query = text("""
                SELECT id, name, instructions, description, created_at, updated_at
                FROM agents 
                WHERE id = :agent_id
            """)
            
            result = session.execute(query, {"agent_id": int(agent_id)})
            row = result.fetchone()
            
            if row:
                return {
                    "id": str(row.id),
                    "name": row.name,
                    "instructions": row.instructions,
                    "description": row.description,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                }
            
            return None
            
        except Exception as e:
            print(f"Ошибка при получении агента {agent_id} из БД: {e}")
            return None


def get_all_agents_from_db() -> List[Dict[str, Any]]:
    """
    Получает все агенты из таблицы agents.
    
    Returns:
        Список словарей с данными всех агентов
    """
    with SessionLocal() as session:
        try:
            # Выполняем запрос к таблице agents
            query = text("""
                SELECT id, name, instructions, description, created_at, updated_at
                FROM agents 
                ORDER BY id
            """)
            
            result = session.execute(query)
            rows = result.fetchall()
            
            agents = []
            for row in rows:
                agents.append({
                    "id": str(row.id),
                    "name": row.name,
                    "instructions": row.instructions,
                    "description": row.description,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                })
            
            return agents
            
        except Exception as e:
            print(f"Ошибка при получении всех агентов из БД: {e}")
            return []


def refresh_agent_cache(agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Обновляет кэш агентов из базы данных.
    
    Args:
        agent_id: ID конкретного агента для обновления (если None, обновляются все)
        
    Returns:
        Результат операции обновления
    """
    try:
        if agent_id:
            # Обновляем конкретного агента
            agent_data = get_agent_from_db(agent_id)
            if agent_data:
                return {
                    "success": True,
                    "message": f"Агент {agent_id} успешно обновлен",
                    "agent": agent_data
                }
            else:
                return {
                    "success": False,
                    "message": f"Агент {agent_id} не найден в БД"
                }
        else:
            # Обновляем всех агентов
            all_agents = get_all_agents_from_db()
            return {
                "success": True,
                "message": f"Успешно обновлено {len(all_agents)} агентов",
                "agents": all_agents,
                "count": len(all_agents)
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка при обновлении кэша агентов: {e}"
        } 