#!/usr/bin/env python3
"""
Простой тест агента с изображением на входе.
"""

import requests
from PIL import Image, ImageDraw
from io import BytesIO

def create_finance_chart():
    """Создает простую финансовую диаграмму"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Заголовок
    draw.text((300, 30), "AAPL Stock Price", fill='black', font_size=24)
    
    # Оси
    draw.line([(100, 500), (700, 500)], fill='black', width=2)  # X axis
    draw.line([(100, 100), (100, 500)], fill='black', width=2)  # Y axis
    
    # Данные (простой восходящий тренд)
    points = [(120, 450), (200, 420), (280, 380), (360, 340), (440, 300), (520, 280), (600, 250), (680, 220)]
    
    # Рисуем линию
    for i in range(len(points)-1):
        draw.line([points[i], points[i+1]], fill='green', width=3)
    
    # Рисуем точки
    for point in points:
        draw.ellipse([point[0]-3, point[1]-3, point[0]+3, point[1]+3], fill='darkgreen')
    
    # Подписи
    draw.text((120, 520), "Jan", fill='black')
    draw.text((280, 520), "Mar", fill='black')  
    draw.text((440, 520), "May", fill='black')
    draw.text((600, 520), "Jul", fill='black')
    
    draw.text((50, 450), "$150", fill='black')
    draw.text((50, 350), "$170", fill='black')
    draw.text((50, 250), "$190", fill='black')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def test_with_chart():
    """Тестируем агента с финансовой диаграммой"""
    print("📊 Создаем финансовую диаграмму...")
    chart = create_finance_chart()
    
    url = "http://localhost:8000/v1/agents/finance_analyst_v1/runs/multipart"
    
    files = {
        'images': ('finance_chart.png', chart.getvalue(), 'image/png')
    }
    
    data = {
        'message': 'Проанализируй эту диаграмму AAPL. Создай улучшенную версию графика и озвучь ключевые выводы о тренде.',
        'stream': 'false'
    }
    
    print("📤 Отправляем запрос...")
    try:
        response = requests.post(url, files=files, data=data, timeout=180)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешно!")
            print(f"📝 Текст: {len(result.get('content', ''))} символов")
            print(f"📸 Изображения: {len(result.get('images', []))}")
            print(f"🎵 Аудио: {len(result.get('audio', []))}")
            
            # Показываем первые 300 символов ответа
            content = result.get('content', '')
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"\n📄 Ответ агента:\n{preview}")
            
            # Проверяем созданные медиа
            images = result.get('images', [])
            if images:
                print(f"\n📸 Созданные изображения:")
                for i, img in enumerate(images):
                    print(f"   {i+1}. {img.get('url', 'N/A')}")
            
            audio_list = result.get('audio', [])
            if audio_list:
                print(f"\n🎵 Созданные аудио:")
                for i, audio in enumerate(audio_list):
                    if 'content' in audio:
                        print(f"   {i+1}. Base64 аудио ({len(audio['content'])} символов)")
                    elif 'url' in audio:
                        print(f"   {i+1}. URL: {audio['url']}")
            
            return True
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

if __name__ == "__main__":
    test_with_chart() 