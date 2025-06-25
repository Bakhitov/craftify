"""
Middleware для интеграции с Supabase Auth.
Обеспечивает аутентификацию и извлечение tenant_id из JWT токенов.
"""

import jwt
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SupabaseAuth:
    """Класс для работы с Supabase Auth"""
    
    def __init__(self, supabase_url: str, supabase_anon_key: str, supabase_jwt_secret: str):
        self.supabase_url = supabase_url
        self.supabase_anon_key = supabase_anon_key
        self.supabase_jwt_secret = supabase_jwt_secret
        self.security = HTTPBearer()
        
        # Кэш для JWT ключей
        self._jwks_cache: Optional[Dict] = None
        self._jwks_cache_expiry: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """
        Верифицирует JWT токен Supabase и извлекает данные пользователя.
        
        Args:
            credentials: JWT токен из заголовка Authorization
            
        Returns:
            Декодированные данные токена с user_id, tenant_id и ролями
            
        Raises:
            HTTPException: При ошибке верификации токена
        """
        try:
            token = credentials.credentials
            
            # Декодируем токен без верификации для получения заголовка
            unverified_header = jwt.get_unverified_header(token)
            
            # Получаем ключи для верификации
            jwks = await self._get_jwks()
            
            # Находим нужный ключ
            key = self._find_key(jwks, unverified_header.get('kid'))
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: key not found"
                )
            
            # Верифицируем и декодируем токен
            payload = jwt.decode(
                token,
                key,
                algorithms=['HS256', 'RS256'],
                audience='authenticated',
                issuer=f"{self.supabase_url}/auth/v1"
            )
            
            # Извлекаем данные пользователя
            user_data = self._extract_user_data(payload)
            
            return user_data
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    async def _get_jwks(self) -> Dict:
        """Получает JWKS ключи от Supabase с кэшированием"""
        now = datetime.utcnow()
        
        # Проверяем кэш
        if (self._jwks_cache and self._jwks_cache_expiry and 
            now < self._jwks_cache_expiry):
            return self._jwks_cache
        
        try:
            # Загружаем ключи от Supabase
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/.well-known/jwks_uri",
                    timeout=10.0
                )
                response.raise_for_status()
                
                jwks = response.json()
                
                # Кэшируем результат
                self._jwks_cache = jwks
                self._jwks_cache_expiry = now + self._cache_ttl
                
                return jwks
                
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # Если есть кэшированные ключи, используем их
            if self._jwks_cache:
                return self._jwks_cache
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify token: JWKS unavailable"
            )
    
    def _find_key(self, jwks: Dict, kid: str) -> Optional[str]:
        """Находит ключ по kid в JWKS"""
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                return key.get('secret') or self.supabase_jwt_secret
        
        # Fallback на секрет из настроек
        return self.supabase_jwt_secret
    
    def _extract_user_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает данные пользователя из JWT payload.
        
        Структура Supabase JWT:
        {
            "sub": "user_id",
            "email": "user@example.com",
            "app_metadata": {
                "tenant_id": "tenant_123",
                "role": "admin"
            },
            "user_metadata": {
                "name": "John Doe"
            }
        }
        """
        user_id = payload.get('sub')
        email = payload.get('email')
        
        # Извлекаем метаданные
        app_metadata = payload.get('app_metadata', {})
        user_metadata = payload.get('user_metadata', {})
        
        # Извлекаем tenant_id (может быть в app_metadata или user_metadata)
        tenant_id = (
            app_metadata.get('tenant_id') or 
            user_metadata.get('tenant_id') or
            user_id  # Fallback: используем user_id как tenant_id для личных аккаунтов
        )
        
        # Извлекаем роли
        roles = app_metadata.get('roles', [])
        if isinstance(roles, str):
            roles = [roles]
        
        # Определяем подписку
        subscription_tier = app_metadata.get('subscription_tier', 'free')
        
        return {
            'user_id': user_id,
            'email': email,
            'tenant_id': tenant_id,
            'roles': roles,
            'subscription_tier': subscription_tier,
            'name': user_metadata.get('name'),
            'app_metadata': app_metadata,
            'user_metadata': user_metadata,
            'raw_payload': payload
        }
    
    async def get_user_permissions(self, user_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Определяет права пользователя на основе ролей и подписки.
        
        Args:
            user_data: Данные пользователя из JWT
            
        Returns:
            Словарь с правами пользователя
        """
        roles = user_data.get('roles', [])
        subscription_tier = user_data.get('subscription_tier', 'free')
        
        permissions = {
            # Базовые права
            'can_use_platform': True,
            'can_view_agents': True,
            'can_run_agents': True,
            
            # Права на создание
            'can_create_agents': subscription_tier in ['basic', 'pro', 'enterprise'],
            'can_create_tools': subscription_tier in ['pro', 'enterprise'],
            'can_create_teams': subscription_tier in ['pro', 'enterprise'],
            'can_create_workflows': subscription_tier == 'enterprise',
            
            # Права на управление
            'can_manage_tenant': 'admin' in roles or 'owner' in roles,
            'can_manage_users': 'admin' in roles or 'owner' in roles,
            'can_view_analytics': subscription_tier in ['pro', 'enterprise'],
            
            # API права
            'can_use_api': True,
            'can_use_webhooks': subscription_tier in ['pro', 'enterprise'],
            
            # Расширенные возможности
            'can_use_advanced_models': subscription_tier in ['pro', 'enterprise'],
            'can_share_agents': subscription_tier in ['basic', 'pro', 'enterprise'],
            'can_export_data': subscription_tier in ['pro', 'enterprise'],
        }
        
        # Специальные роли
        if 'platform_admin' in roles:
            permissions.update({
                'can_manage_platform': True,
                'can_view_all_tenants': True,
                'can_modify_static_agents': True,
            })
        
        return permissions


# Глобальный экземпляр для использования в приложении
supabase_auth: Optional[SupabaseAuth] = None

def init_supabase_auth(supabase_url: str, supabase_anon_key: str, supabase_jwt_secret: str):
    """Инициализирует Supabase Auth"""
    global supabase_auth
    supabase_auth = SupabaseAuth(supabase_url, supabase_anon_key, supabase_jwt_secret)
    return supabase_auth


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency для получения текущего пользователя из JWT токена.
    
    Returns:
        Данные пользователя из Supabase Auth
    """
    if not supabase_auth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase Auth not initialized"
        )
    
    # Получаем токен из заголовка
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(' ')[1]
    credentials = type('Credentials', (), {'credentials': token})()
    
    # Верифицируем токен и получаем данные пользователя
    user_data = await supabase_auth.verify_token(credentials)
    
    return user_data


async def get_current_tenant_id(request: Request) -> str:
    """
    Dependency для получения tenant_id текущего пользователя.
    
    Returns:
        ID тенанта
    """
    user_data = await get_current_user(request)
    return user_data['tenant_id']


async def require_permission(permission: str):
    """
    Dependency для проверки конкретного права пользователя.
    
    Args:
        permission: Название права для проверки
    """
    async def check_permission(request: Request) -> Dict[str, Any]:
        user_data = await get_current_user(request)
        
        if not supabase_auth:
            raise HTTPException(status_code=500, detail="Auth not initialized")
        
        permissions = await supabase_auth.get_user_permissions(user_data)
        
        if not permissions.get(permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        
        return user_data
    
    return check_permission


# Готовые dependency для частых случаев
async def require_agent_creation(request: Request) -> Dict[str, Any]:
    """Проверяет право на создание агентов"""
    return await require_permission('can_create_agents')(request)

async def require_tool_creation(request: Request) -> Dict[str, Any]:
    """Проверяет право на создание инструментов"""
    return await require_permission('can_create_tools')(request)

async def require_tenant_admin(request: Request) -> Dict[str, Any]:
    """Проверяет права администратора тенанта"""
    return await require_permission('can_manage_tenant')(request) 