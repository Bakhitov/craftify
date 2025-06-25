"""
API для управления динамическими инструментами.
Предоставляет CRUD операции для инструментов в БД.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from db.session import SessionLocal
import json


# Pydantic модели для API
class ToolRequest(BaseModel):
    name: str
    tool_id: str
    description: Optional[str] = None
    function_name: str
    parameters_schema: Dict[str, Any]
    implementation: str


class ToolResponse(BaseModel):
    id: int
    name: str
    tool_id: str
    description: Optional[str]
    function_name: str
    parameters_schema: Dict[str, Any]
    implementation: str
    is_active: bool
    created_at: str
    updated_at: str


# Создаем роутер
router = APIRouter(prefix="/dynamic-tools", tags=["Dynamic Tools"])


@router.get("/", response_model=List[ToolResponse])
async def get_dynamic_tools():
    """Получить список всех динамических инструментов"""
    with SessionLocal() as session:
        try:
            query = text("""
                SELECT id, name, tool_id, description, function_name,
                       parameters_schema, implementation, is_active, 
                       created_at, updated_at
                FROM dynamic_tools
                ORDER BY created_at DESC
            """)
            
            result = session.execute(query)
            tools = []
            
            for row in result.fetchall():
                tools.append({
                    "id": row.id,
                    "name": row.name,
                    "tool_id": row.tool_id,
                    "description": row.description,
                    "function_name": row.function_name,
                    "parameters_schema": row.parameters_schema or {},
                    "implementation": row.implementation,
                    "is_active": row.is_active,
                    "created_at": row.created_at.isoformat(),
                    "updated_at": row.updated_at.isoformat()
                })
            
            return tools
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при получении инструментов: {str(e)}"
            )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_dynamic_tool(tool_id: str):
    """Получить динамический инструмент по ID"""
    with SessionLocal() as session:
        try:
            query = text("""
                SELECT id, name, tool_id, description, function_name,
                       parameters_schema, implementation, is_active,
                       created_at, updated_at
                FROM dynamic_tools
                WHERE tool_id = :tool_id
            """)
            
            result = session.execute(query, {"tool_id": tool_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Инструмент с ID '{tool_id}' не найден"
                )
            
            return {
                "id": row.id,
                "name": row.name,
                "tool_id": row.tool_id,
                "description": row.description,
                "function_name": row.function_name,
                "parameters_schema": row.parameters_schema or {},
                "implementation": row.implementation,
                "is_active": row.is_active,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при получении инструмента: {str(e)}"
            )


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_tool_code(tool_data: ToolRequest):
    """Валидирует код инструмента перед созданием"""
    from agents.dynamic.tool_factory import DynamicToolFactory
    
    try:
        # Валидируем код инструмента
        validation_result = DynamicToolFactory.validate_tool_code(
            tool_data.implementation,
            tool_data.function_name
        )
        
        return {
            "valid": validation_result["valid"],
            "message": validation_result.get("message", validation_result.get("error"))
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Ошибка валидации: {str(e)}"
        }


@router.post("/", response_model=ToolResponse)
async def create_dynamic_tool(tool_data: ToolRequest):
    """Создать новый динамический инструмент"""
    with SessionLocal() as session:
        try:
            # Проверяем уникальность tool_id
            check_query = text("SELECT id FROM dynamic_tools WHERE tool_id = :tool_id")
            existing = session.execute(check_query, {"tool_id": tool_data.tool_id}).fetchone()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Инструмент с ID '{tool_data.tool_id}' уже существует"
                )
            
            # Создаем новый инструмент
            insert_query = text("""
                INSERT INTO dynamic_tools 
                (name, tool_id, description, function_name, parameters_schema, implementation)
                VALUES (:name, :tool_id, :description, :function_name, :parameters_schema, :implementation)
                RETURNING id, created_at, updated_at
            """)
            
            result = session.execute(insert_query, {
                "name": tool_data.name,
                "tool_id": tool_data.tool_id,
                "description": tool_data.description,
                "function_name": tool_data.function_name,
                "parameters_schema": json.dumps(tool_data.parameters_schema),
                "implementation": tool_data.implementation
            })
            
            row = result.fetchone()
            session.commit()
            
            return {
                "id": row.id,
                "name": tool_data.name,
                "tool_id": tool_data.tool_id,
                "description": tool_data.description,
                "function_name": tool_data.function_name,
                "parameters_schema": tool_data.parameters_schema,
                "implementation": tool_data.implementation,
                "is_active": True,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании инструмента: {str(e)}"
            )
