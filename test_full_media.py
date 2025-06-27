#!/usr/bin/env python3
"""
Полный тест агента finance_analyst_v1 с медиа входом и выходом.
"""

import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def create_finance_chart_base64():
    """Создает финансовую диаграмму и возвращает base64"""
    # Создаем изображение
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Заголовок
    draw.text((280, 30), "AAPL Stock Analysis", fill='black')
    
    # Оси координат
    draw.line([(100, 500), (700, 500)], fill='black', width=2)  # X ось
    draw.line([(100, 100), (100, 500)], fill='black', width=2)  # Y ось
    
    # Подписи осей
    draw.text((400, 520), "Time", fill='black')
    draw.text((20, 300), "Price ($)", fill='black')
    
    # Данные графика (восходящий тренд)
    points = [
        (120, 450), (180, 420), (240, 380), (300, 360), 
        (360, 340), (420, 310), (480, 290), (540, 270), 
        (600, 250), (660, 230)
    ]
    
    # Рисуем линию тренда
    for i in range(len(points)-1):
        draw.line([points[i], points[i+1]], fill='green', width=3)
    
    # Добавляем точки
    for point in points:
        draw.ellipse([point[0]-3, point[1]-3, point[0]+3, point[1]+3], fill='blue')
    
    # Добавляем цены
    prices = ['$150', '$155', '$162', '$168', '$175', '$182', '$189', '$195', '$202', '$210']
    for i, (point, price) in enumerate(zip(points, prices)):
        if i % 2 == 0:  # Показываем каждую вторую цену
            draw.text((point[0]-10, point[1]-20), price, fill='blue')
    
    # Конвертируем в base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"

def test_agent_with_media():
    """Тестирует агента с медиа входом и выходом"""
    
    print("🎯 Тестирование finance_analyst_v1 с медиа...")
    
    # Создаем тестовое изображение
    image_data = create_finance_chart_base64()
    print(f"✅ Создано тестовое изображение ({len(image_data)} символов)")
    
    # Тест 1: Анализ изображения + создание аудио отчета
    print("\n📊 Тест 1: Анализ графика + аудио отчет")
    
    payload = {
        "message": "Проанализируй этот график акций AAPL. Определи тренд, ключевые уровни поддержки и сопротивления. Создай краткий аудио-отчет с выводами на русском языке.",
        "images": [image_data]
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/agents/finance_analyst_v1/runs",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успешный ответ агента:")
            print(f"📝 Текст: {data.get('message', 'Нет текста')[:200]}...")
            
            # Проверяем наличие аудио
            if 'audio' in str(data):
                print("🎵 Аудио файл создан!")
            
            # Проверяем наличие изображений
            if 'images' in str(data):
                print("🖼️ Изображения найдены в ответе!")
                
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.Timeout:
        print("⏰ Тайм-аут запроса (это нормально для больших медиа)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 2: Создание диаграммы + аудио презентация
    print("\n🎨 Тест 2: Создание диаграммы + аудио презентация")
    
    payload2 = {
        "message": "Создай диаграмму с прогнозом роста акций Apple на следующий квартал. Затем создай аудио-презентацию этого прогноза для инвесторов."
    }
    
    try:
        response2 = requests.post(
            "http://localhost:8000/v1/agents/finance_analyst_v1/runs",
            json=payload2,
            timeout=60
        )
        
        if response2.status_code == 200:
            data2 = response2.json()
            print("✅ Успешное создание контента:")
            print(f"📝 Текст: {data2.get('message', 'Нет текста')[:200]}...")
            
            # Считаем медиа элементы
            response_str = str(data2)
            images_count = response_str.count('https://oaidalleapiprodscus.blob.core.windows.net/')
            audio_count = response_str.count('base64') - response_str.count('data:image')
            
            print(f"🖼️ Создано изображений: {images_count}")
            print(f"🎵 Создано аудио файлов: {audio_count}")
            
        else:
            print(f"❌ Ошибка API: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_agent_with_media() 