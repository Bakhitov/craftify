#!/usr/bin/env python3
"""
Исправленный комплексный тест мультимодальности Agent API Platform
Обрабатывает аудио файлы как обычные файлы
"""

import requests
import time
import json
import os
from pathlib import Path

class MultimodalTesterFixed:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_files_dir = Path("test_file")
        
    def test_single_file(self, file_path: Path, agent_id="agno_assist"):
        """Тестирует один файл с правильным определением типа"""
        print(f"\n🔍 Тестирую файл: {file_path.name}")
        print(f"📊 Размер: {file_path.stat().st_size / 1024:.1f} KB")
        
        # Определяем тип файла и соответствующий параметр
        file_ext = file_path.suffix.lower()
        
        # Маппинг расширений к типам мультимедиа
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        audio_exts = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        
        # Готовим данные для запроса
        files_data = {}
        form_data = {
            'message': f'Проанализируй этот файл {file_path.name} и дай подробную информацию о его содержимом',
            'stream': 'false',
            'model': 'gpt-4.1'
        }
        
        try:
            with open(file_path, 'rb') as f:
                if file_ext in image_exts:
                    files_data['images'] = (file_path.name, f, 'image/*')
                elif file_ext in audio_exts:
                    # 🔧 ИСПРАВЛЕНИЕ: Аудио файлы обрабатываем как обычные файлы
                    files_data['files'] = (file_path.name, f, 'audio/*')
                    form_data['message'] = f'Это аудио файл {file_path.name}. Проанализируй его метаданные и расскажи что можешь определить о нем.'
                elif file_ext in video_exts:
                    files_data['videos'] = (file_path.name, f, 'video/*')
                else:
                    # Все остальные файлы как files
                    files_data['files'] = (file_path.name, f, 'application/octet-stream')
                
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}/v1/agents/{agent_id}/runs/multipart",
                    data=form_data,
                    files=files_data,
                    timeout=300  # 5 минут таймаут
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('content', '')
                    
                    print(f"✅ Успешно обработан за {elapsed:.2f}с")
                    print(f"📝 Длина ответа: {len(content)} символов")
                    
                    # Проверяем мультимедиа в ответе
                    images = result.get('images', [])
                    audio = result.get('audio', [])
                    videos = result.get('videos', [])
                    response_audio = result.get('response_audio')
                    
                    if images:
                        print(f"🖼️ Сгенерированные изображения: {len(images)}")
                    if audio:
                        print(f"🎵 Сгенерированные аудио: {len(audio)}")
                    if videos:
                        print(f"🎬 Сгенерированные видео: {len(videos)}")
                    if response_audio:
                        print(f"🎤 Аудио ответ агента: Да")
                    
                    # Показываем первые 500 символов ответа
                    preview = content[:500] + "..." if len(content) > 500 else content
                    print(f"\n📄 Ответ агента:\n{preview}")
                    
                    return True, elapsed, len(content)
                    
                else:
                    print(f"❌ Ошибка {response.status_code}: {response.text[:200]}")
                    return False, elapsed, 0
                    
        except Exception as e:
            print(f"❌ Исключение: {e}")
            return False, 0, 0
    
    def run_comprehensive_test(self):
        """Запускает полный комплексный тест с исправлениями"""
        print("🎯 ИСПРАВЛЕННЫЙ КОМПЛЕКСНЫЙ ТЕСТ МУЛЬТИМОДАЛЬНОСТИ")
        print("=" * 60)
        
        if not self.test_files_dir.exists():
            print(f"❌ Папка {self.test_files_dir} не найдена")
            return
        
        # Получаем все файлы
        all_files = [f for f in self.test_files_dir.iterdir() 
                    if f.is_file() and f.name != '.DS_Store']
        
        if not all_files:
            print("❌ Нет файлов для тестирования")
            return
        
        print(f"📁 Найдено файлов: {len(all_files)}")
        
        # Группируем файлы по типам
        file_types = {
            'images': [],
            'audio': [],
            'videos': [],
            'documents': []
        }
        
        for file_path in all_files:
            ext = file_path.suffix.lower()
            if ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}:
                file_types['images'].append(file_path)
            elif ext in {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}:
                file_types['audio'].append(file_path)
            elif ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
                file_types['videos'].append(file_path)
            else:
                file_types['documents'].append(file_path)
        
        print(f"🖼️ Изображения: {len(file_types['images'])}")
        print(f"🎵 Аудио (как файлы): {len(file_types['audio'])}")
        print(f"🎬 Видео: {len(file_types['videos'])}")
        print(f"📄 Документы: {len(file_types['documents'])}")
        
        # Тестируем каждый файл индивидуально
        print(f"\n📋 ИНДИВИДУАЛЬНОЕ ТЕСТИРОВАНИЕ ФАЙЛОВ")
        print("-" * 50)
        
        successful_tests = 0
        total_time = 0
        total_response_length = 0
        
        for file_path in all_files:
            success, elapsed, response_length = self.test_single_file(file_path)
            if success:
                successful_tests += 1
                total_time += elapsed
                total_response_length += response_length
            
            time.sleep(1)  # Небольшая пауза между запросами
        
        # Итоговая статистика
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)
        print(f"✅ Успешно обработано файлов: {successful_tests}/{len(all_files)}")
        print(f"⏱️ Общее время обработки: {total_time:.2f}с")
        print(f"⚡ Среднее время на файл: {total_time/max(successful_tests, 1):.2f}с")
        print(f"📝 Общая длина ответов: {total_response_length} символов")
        
        # Процент успеха
        success_rate = (successful_tests / len(all_files)) * 100
        print(f"🎯 Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("🏆 ОТЛИЧНЫЙ РЕЗУЛЬТАТ! Мультимодальность работает превосходно!")
        elif success_rate >= 85:
            print("👍 ХОРОШИЙ РЕЗУЛЬТАТ! Есть небольшие проблемы для исправления")
        else:
            print("⚠️ ТРЕБУЕТСЯ ДОРАБОТКА! Много ошибок в обработке файлов")

def main():
    tester = MultimodalTesterFixed()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
