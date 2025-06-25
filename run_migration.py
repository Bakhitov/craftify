#!/usr/bin/env python3
"""
Скрипт для запуска миграций Alembic с переменными окружения.
"""
import os
import subprocess
import sys

# Устанавливаем переменные окружения
os.environ['DB_URL'] = 'postgresql://postgres:Ginifi51!@db.wyehpfzafbjfvyjzgjss.supabase.co:5432/postgres'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'Ginifi51!'
os.environ['DB_NAME'] = 'postgres'
os.environ['DB_PORT'] = '5432'

def run_migration():
    """Запускает миграцию Alembic"""
    try:
        # Переходим в директорию с миграциями
        os.chdir('db/migrations')
        
        # Запускаем миграцию
        result = subprocess.run(['alembic', 'upgrade', 'head'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Миграция выполнена успешно!")
            print(result.stdout)
        else:
            print("❌ Ошибка при выполнении миграции:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1) 