"""
Простой и быстрый кэш с TTL - оптимизированная версия.
Принципы: минимум накладных расходов, максимум производительности.
"""
import time
from typing import Any, Optional, Dict, List


class SimpleCache:
    """
    Быстрый in-memory кэш с TTL.
    Оптимизирован для скорости и простоты.
    """
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Any] = {}
        self._ttl_cache: Dict[str, float] = {}  # Отдельный кэш для TTL
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Быстрое получение значения с проверкой TTL"""
        # Быстрая проверка существования
        if key not in self._cache:
            return None
        
        # Проверка TTL
        if key in self._ttl_cache:
            if time.time() > self._ttl_cache[key]:
                # Истек - удаляем сразу
                self._remove_key(key)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Быстрое сохранение значения"""
        try:
            self._cache[key] = value
            
            # Устанавливаем TTL
            expire_time = time.time() + (ttl or self._default_ttl)
            self._ttl_cache[key] = expire_time
            
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Удаление ключа"""
        if key in self._cache:
            self._remove_key(key)
            return True
        return False
    
    def clear(self) -> None:
        """Полная очистка кэша"""
        self._cache.clear()
        self._ttl_cache.clear()
    
    def _remove_key(self, key: str) -> None:
        """Внутренний метод удаления ключа"""
        self._cache.pop(key, None)
        self._ttl_cache.pop(key, None)
    
    def has(self, key: str) -> bool:
        """Проверяет существование ключа (с проверкой TTL)"""
        return self.get(key) is not None
    
    def size(self) -> int:
        """Количество элементов в кэше"""
        return len(self._cache)
    
    def cleanup(self) -> int:
        """
        Быстрая очистка истекших элементов.
        Возвращает количество удаленных элементов.
        """
        current_time = time.time()
        expired_keys = []
        
        # Находим истекшие ключи
        for key, expire_time in self._ttl_cache.items():
            if current_time > expire_time:
                expired_keys.append(key)
        
        # Удаляем истекшие ключи
        for key in expired_keys:
            self._remove_key(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Быстрая статистика кэша"""
        current_time = time.time()
        expired_count = sum(1 for expire_time in self._ttl_cache.values() 
                          if current_time > expire_time)
        
        return {
            "total_keys": len(self._cache),
            "expired_keys": expired_count,
            "active_keys": len(self._cache) - expired_count,
            "default_ttl": self._default_ttl
        }
    
    # Батчевые операции для производительности
    def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """Батчевое сохранение нескольких элементов"""
        success_count = 0
        expire_time = time.time() + (ttl or self._default_ttl)
        
        for key, value in items.items():
            try:
                self._cache[key] = value
                self._ttl_cache[key] = expire_time
                success_count += 1
            except Exception:
                continue
        
        return success_count
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Батчевое получение нескольких элементов"""
        result = {}
        current_time = time.time()
        
        for key in keys:
            if key in self._cache:
                # Проверяем TTL
                if key in self._ttl_cache and current_time > self._ttl_cache[key]:
                    self._remove_key(key)
                    continue
                
                result[key] = self._cache[key]
        
        return result
    
    def delete_many(self, keys: List[str]) -> int:
        """Батчевое удаление нескольких элементов"""
        deleted_count = 0
        for key in keys:
            if key in self._cache:
                self._remove_key(key)
                deleted_count += 1
        
        return deleted_count 