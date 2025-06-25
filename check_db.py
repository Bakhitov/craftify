#!/usr/bin/env python3
"""
Скрипт для проверки состояния базы данных
"""
import os
import sys
from sqlalchemy import create_engine, text
from db.url import get_db_url

def check_database():
    """Проверяет состояние базы данных и наличие таблиц"""
    try:
        # Получаем URL базы данных
        db_url = get_db_url()
        print(f"🔗 Подключение к БД: {db_url.split('@')[0]}@***")
        
        # Создаем подключение
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            print("✅ Подключение к базе данных успешно!")
            
            # Проверяем текущую схему
            result = connection.execute(text("SELECT current_schema()"))
            current_schema = result.scalar()
            print(f"📋 Текущая схема: {current_schema}")
            
            # Проверяем доступные схемы
            result = connection.execute(text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"))
            schemas = [row[0] for row in result.fetchall()]
            print(f"📁 Доступные схемы: {', '.join(schemas)}")
            
            # Проверяем таблицы в текущей схеме
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = current_schema()
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"📊 Таблицы в схеме '{current_schema}': {', '.join(tables) if tables else 'НЕТ ТАБЛИЦ'}")
            
            # Проверяем таблицы в схеме public
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            public_tables = [row[0] for row in result.fetchall()]
            print(f"📊 Таблицы в схеме 'public': {', '.join(public_tables) if public_tables else 'НЕТ ТАБЛИЦ'}")
            
            # Проверяем конкретно таблицу dynamic_agents
            result = connection.execute(text("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_name = 'dynamic_agents'
            """))
            dynamic_agents_tables = result.fetchall()
            if dynamic_agents_tables:
                for schema, table in dynamic_agents_tables:
                    print(f"🎯 Найдена таблица 'dynamic_agents' в схеме: {schema}")
            else:
                print("❌ Таблица 'dynamic_agents' не найдена ни в одной схеме!")
            
            # Проверяем историю миграций Alembic
            try:
                result = connection.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                print(f"🔄 Текущая версия миграции Alembic: {version}")
            except Exception as e:
                print(f"⚠️ Ошибка при проверке версии Alembic: {e}")
            
            # Проверяем search_path
            result = connection.execute(text("SHOW search_path"))
            search_path = result.scalar()
            print(f"🔍 Search path: {search_path}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Проверка состояния базы данных...")
    print("=" * 50)
    
    # Загружаем переменные окружения из .env файла если он есть
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 Загружены переменные из .env файла")
    
    success = check_database()
    
    if not success:
        sys.exit(1)
    
    print("=" * 50)
    print("✅ Проверка завершена!") 