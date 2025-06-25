#!/usr/bin/env python3
"""
Скрипт для сброса состояния миграций Alembic.
"""
import os
import subprocess
import sys

# Устанавливаем переменные окружения
db_url = 'postgresql://postgres:Ginifi51!@db.wyehpfzafbjfvyjzgjss.supabase.co:5432/postgres'
os.environ['DB_URL'] = db_url
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'Ginifi51!'
os.environ['DB_NAME'] = 'postgres'
os.environ['DB_PORT'] = '5432'

def run_command(command):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    # Переходим в директорию с миграциями
    os.chdir('db/migrations')
    
    print("🔄 Сбрасываем состояние миграций...")
    
    # Помечаем текущую миграцию как базовую
    print("\n1️⃣ Помечаем текущую версию как базовую...")
    code, stdout, stderr = run_command('alembic stamp base')
    if code == 0:
        print("✅ Состояние сброшено до base")
        print(stdout)
    else:
        print(f"❌ Ошибка при сбросе: {stderr}")
        return False
    
    # Применяем нашу миграцию
    print("\n2️⃣ Применяем миграцию динамических сущностей...")
    code, stdout, stderr = run_command('alembic upgrade head')
    if code == 0:
        print("✅ Миграция применена успешно!")
        print(stdout)
    else:
        print(f"❌ Ошибка при применении миграции: {stderr}")
        return False
    
    # Проверяем результат
    print("\n3️⃣ Проверяем текущее состояние...")
    code, stdout, stderr = run_command('alembic current')
    if code == 0:
        print("✅ Текущее состояние:")
        print(stdout)
    else:
        print(f"❌ Ошибка при проверке: {stderr}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 