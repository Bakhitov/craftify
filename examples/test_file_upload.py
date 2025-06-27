#!/usr/bin/env python3
"""
Скрипт для тестирования нового эндпоинта с поддержкой файлов.
Демонстрирует загрузку различных типов файлов через multipart/form-data.
"""

import asyncio
import aiofiles
import httpx
from pathlib import Path
import tempfile
import base64

# Настройки API
BASE_URL = "http://localhost:8000"
AGENT_ID = "web_agent"  # Можно тестировать с любым агентом

async def create_test_files():
    """Создает тестовые файлы для загрузки"""
    temp_dir = Path(tempfile.gettempdir()) / "agent_api_test"
    temp_dir.mkdir(exist_ok=True)
    
    # Создаем тестовый текстовый файл
    text_file = temp_dir / "test_document.txt"
    async with aiofiles.open(text_file, 'w', encoding='utf-8') as f:
        await f.write("""
Тестовый документ для анализа

Это документ содержит важную информацию:
1. Первый пункт - основные данные
2. Второй пункт - дополнительная информация  
3. Третий пункт - выводы и рекомендации

Ключевые слова: тестирование, анализ, документ, агенты
        """.strip())
    
    # Создаем тестовый Python файл
    python_file = temp_dir / "test_code.py"
    async with aiofiles.open(python_file, 'w', encoding='utf-8') as f:
        await f.write("""
def hello_world():
    \"\"\"Простая функция для демонстрации\"\"\"
    print("Hello from Agent API!")
    return "success"

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

if __name__ == "__main__":
    hello_world()
    test = TestClass("Agent")
    print(test.greet())
        """.strip())
    
    # Создаем тестовый CSV файл
    csv_file = temp_dir / "test_data.csv"
    async with aiofiles.open(csv_file, 'w', encoding='utf-8') as f:
        await f.write("""
Name,Age,City,Salary
Иван Иванов,30,Москва,50000
Мария Петрова,25,СПб,45000
Алексей Сидоров,35,Екатеринбург,40000
Елена Козлова,28,Новосибирск,42000
        """.strip())
    
    return {
        'text': text_file,
        'python': python_file,
        'csv': csv_file
    }

async def test_single_file_upload():
    """Тестирует загрузку одного файла"""
    print("🧪 Тестируем загрузку одного текстового файла...")
    
    test_files = await create_test_files()
    
    async with httpx.AsyncClient() as client:
        async with aiofiles.open(test_files['text'], 'rb') as f:
            file_content = await f.read()
        
        files = {
            'files': (test_files['text'].name, file_content, 'text/plain')
        }
        
        data = {
            'message': 'Проанализируй содержимое загруженного документа и выдели ключевые моменты',
            'stream': 'false',
            'model': 'gpt-4.1'
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/v1/agents/{AGENT_ID}/runs/multipart",
                files=files,
                data=data,
                timeout=30.0
            )
            
            print(f"✅ Статус: {response.status_code}")
            if response.status_code == 200:
                print(f"📄 Ответ: {response.text[:200]}...")
            else:
                print(f"❌ Ошибка: {response.text}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")

async def test_multiple_files_upload():
    """Тестирует загрузку нескольких файлов разных типов"""
    print("\n🧪 Тестируем загрузку нескольких файлов...")
    
    test_files = await create_test_files()
    
    async with httpx.AsyncClient() as client:
        # Читаем все файлы
        files_data = []
        
        # Текстовый файл
        async with aiofiles.open(test_files['text'], 'rb') as f:
            files_data.append(('files', (test_files['text'].name, await f.read(), 'text/plain')))
        
        # Python файл
        async with aiofiles.open(test_files['python'], 'rb') as f:
            files_data.append(('files', (test_files['python'].name, await f.read(), 'text/x-python')))
        
        # CSV файл
        async with aiofiles.open(test_files['csv'], 'rb') as f:
            files_data.append(('files', (test_files['csv'].name, await f.read(), 'text/csv')))
        
        data = {
            'message': 'У меня есть несколько файлов: документ, код на Python и данные CSV. Проанализируй их содержимое и дай краткий обзор каждого файла.',
            'stream': 'false',
            'model': 'gpt-4.1'
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/v1/agents/{AGENT_ID}/runs/multipart",
                files=files_data,
                data=data,
                timeout=60.0
            )
            
            print(f"✅ Статус: {response.status_code}")
            if response.status_code == 200:
                print(f"📄 Ответ: {response.text[:300]}...")
            else:
                print(f"❌ Ошибка: {response.text}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов эндпоинта с поддержкой файлов")
    print("=" * 60)
    
    # Проверяем доступность API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/v1/health", timeout=5.0)
            if response.status_code != 200:
                print(f"❌ API недоступен: {response.status_code}")
                return
    except Exception as e:
        print(f"❌ Не удается подключиться к API: {e}")
        return
    
    print("✅ API доступен, начинаем тесты...\n")
    
    # Запускаем тесты
    await test_single_file_upload()
    await test_multiple_files_upload()
    
    print("\n" + "=" * 60)
    print("🏁 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main()) 