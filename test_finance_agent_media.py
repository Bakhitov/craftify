#!/usr/bin/env python3
"""
Тестирование агента finance_analyst_v1 с медиа входом и выходом.
"""

import requests
import json
import os
from io import BytesIO
import base64

# Конфигурация
API_BASE = "http://localhost:8000/v1"
AGENT_ID = "finance_analyst_v1"

def create_test_image():
    """Создает простое тестовое изображение в формате PNG"""
    from PIL import Image, ImageDraw, ImageFont
    
    # Создаем изображение с графиком
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Рисуем простой график
    draw.rectangle([100, 100, 700, 500], outline='black', width=2)
    draw.text((300, 50), "Финансовый График", fill='black')
    
    # Рисуем линию тренда
    points = [(150, 400), (250, 350), (350, 300), (450, 280), (550, 250), (650, 220)]
    for i in range(len(points)-1):
        draw.line([points[i], points[i+1]], fill='blue', width=3)
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def test_agent_with_text_only():
    """Тест 1: Только текстовый запрос"""
    print("🔍 ТЕСТ 1: Текстовый запрос к агенту")
    
    url = f"{API_BASE}/agents/{AGENT_ID}/runs"
    data = {
        "message": "Проанализируй курс AAPL за последний месяц и создай изображение с графиком трендов. Также озвучь краткую сводку."
    }
    
    print(f"🌐 URL: {url}")
    print(f"📤 Отправляем запрос...")
    
    try:
        response = requests.post(url, json=data, timeout=120)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ответ получен, длина: {len(result.get('content', ''))}")
            print(f"📸 Изображения: {len(result.get('images', []))}")
            print(f"🎵 Аудио: {len(result.get('audio', []))}")
            
            # Сохраняем результат
            with open('test_result_text_only.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def test_agent_with_image():
    """Тест 2: Запрос с изображением на входе"""
    print("\n🔍 ТЕСТ 2: Запрос с изображением на входе")
    
    # Создаем тестовое изображение
    test_img = create_test_image()
    
    url = f"{API_BASE}/agents/{AGENT_ID}/runs/multipart"
    
    files = {
        'images': ('test_chart.png', test_img.getvalue(), 'image/png')
    }
    
    data = {
        'message': 'Проанализируй этот финансовый график и создай детальный отчет. Также создай улучшенную версию графика и озвучь ключевые выводы.',
        'stream': 'false'
    }
    
    print(f"🌐 URL: {url}")
    print(f"📤 Отправляем запрос с изображением...")
    
    try:
        response = requests.post(url, files=files, data=data, timeout=180)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ответ получен, длина: {len(result.get('content', ''))}")
            print(f"📸 Изображения: {len(result.get('images', []))}")
            print(f"🎵 Аудио: {len(result.get('audio', []))}")
            
            # Сохраняем результат
            with open('test_result_with_image.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
            return result
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def test_simple_request():
    """Простой тест для проверки базовой функциональности"""
    print("\n🔍 ТЕСТ ПРОСТОЙ: Базовый запрос")
    
    url = f"{API_BASE}/agents/{AGENT_ID}/runs"
    data = {
        "message": "Привет! Создай простое изображение с логотипом компании Apple и озвучь короткое приветствие."
    }
    
    print(f"🌐 URL: {url}")
    print(f"📤 Отправляем простой запрос...")
    
    try:
        response = requests.post(url, json=data, timeout=120)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ответ получен!")
            print(f"📝 Контент: {len(result.get('content', ''))} символов")
            print(f"📸 Изображения: {len(result.get('images', []))}")
            print(f"🎵 Аудио: {len(result.get('audio', []))}")
            print(f"🎵 Response Audio: {'Да' if result.get('response_audio') else 'Нет'}")
            
            # Показываем первые 200 символов ответа
            content = result.get('content', '')
            if content:
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"📄 Превью ответа: {preview}")
            
            # Сохраняем результат
            with open('test_result_simple.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def analyze_results():
    """Анализ результатов тестирования"""
    print("\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
    
    files_to_check = [
        'test_result_simple.json',
        'test_result_text_only.json',
        'test_result_with_image.json'
    ]
    
    for file_name in files_to_check:
        if os.path.exists(file_name):
            print(f"✅ {file_name} создан")
            
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"   📝 Контент: {len(data.get('content', ''))} символов")
            print(f"   📸 Изображения: {len(data.get('images', []))}")
            print(f"   🎵 Аудио: {len(data.get('audio', []))}")
            print(f"   🎵 Response Audio: {'Да' if data.get('response_audio') else 'Нет'}")
            
            # Проверяем аудио файлы
            audio_list = data.get('audio', [])
            for i, audio_item in enumerate(audio_list):
                if isinstance(audio_item, dict):
                    print(f"   🎵 Аудио {i+1}: {audio_item}")
                    
            # Проверяем response_audio
            response_audio = data.get('response_audio')
            if response_audio:
                print(f"   🎵 Response Audio: {response_audio}")
                    
            # Проверяем изображения
            images_list = data.get('images', [])
            for i, img_item in enumerate(images_list):
                if isinstance(img_item, dict):
                    print(f"   📸 Изображение {i+1}: {img_item}")
        else:
            print(f"❌ {file_name} не найден")

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ АГЕНТА finance_analyst_v1")
    print("=" * 60)
    
    # Проверка доступности API
    try:
        print(f"🔍 Проверяем API: {API_BASE}/health")
        health_response = requests.get(f"{API_BASE}/health", timeout=10)
        print(f"Health статус: {health_response.status_code}")
        if health_response.status_code != 200:
            print("❌ API недоступен")
            return
    except Exception as e:
        print(f"❌ Не удается подключиться к API: {e}")
        return
    
    print("✅ API доступен")
    
    # Проверяем доступность агента
    try:
        agents_response = requests.get(f"{API_BASE}/agents", timeout=10)
        if agents_response.status_code == 200:
            agents = agents_response.json()
            agent_found = False
            for agent in agents:
                if agent.get('agent_id') == AGENT_ID:
                    agent_found = True
                    print(f"✅ Агент {AGENT_ID} найден")
                    break
            
            if not agent_found:
                print(f"❌ Агент {AGENT_ID} не найден")
                return
        else:
            print("❌ Не удается получить список агентов")
            return
    except Exception as e:
        print(f"❌ Ошибка при проверке агентов: {e}")
        return
    
    # Выполняем тесты
    test_simple_request()
    test_agent_with_text_only()
    test_agent_with_image()
    
    # Анализируем результаты
    analyze_results()
    
    print("\n🎯 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print("\nПроверьте созданные файлы:")
    print("- test_result_simple.json")
    print("- test_result_text_only.json")
    print("- test_result_with_image.json")
    
    # Проверяем созданные аудио файлы
    audio_dir = "audio_generations"
    if os.path.exists(audio_dir):
        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
        if audio_files:
            print(f"\n🎵 Созданные аудио файлы ({len(audio_files)}):")
            for audio_file in audio_files:
                file_path = os.path.join(audio_dir, audio_file)
                file_size = os.path.getsize(file_path)
                print(f"   - {audio_file} ({file_size} байт)")

if __name__ == "__main__":
    main() 