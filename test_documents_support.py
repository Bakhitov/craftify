#!/usr/bin/env python3
"""
Тест улучшенной поддержки различных форматов документов
"""
import asyncio
import json
import base64
from pathlib import Path
import httpx

async def test_document_support():
    """Тестирует улучшенную поддержку различных форматов документов"""
    
    # Тестовые файлы с подробной информацией
    test_files = {
        "DOCX": {
            "path": "test_file/Протокол_взаимодействия_онлайн_09.docx",
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "description": "Word документ (протокол)"
        },
        "XLSX": {
            "path": "test_file/FINCAS.xlsx", 
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "description": "Excel таблица (финансовые данные)"
        },
        "PPTX": {
            "path": "test_file/qazaccess.pptx",
            "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "description": "PowerPoint презентация"
        },
        "RTF": {
            "path": "test_file/agnoMCP.rtf",
            "mime": "text/rtf",
            "description": "RTF документ"
        },
        "PDF": {
            "path": "test_file/36871993-08-06-2025.pdf",
            "mime": "application/pdf",
            "description": "PDF документ"
        }
    }
    
    base_url = "http://localhost:8000"
    
    print("🔍 Тестирование улучшенной поддержки документов")
    print("=" * 60)
    
    # Тест через multipart/form-data
    print("\n📤 Тестирование через Multipart API\n")
    
    for doc_type, doc_info in test_files.items():
        file_path = doc_info["path"]
        
        if not Path(file_path).exists():
            print(f"⚠️  {doc_type}: Файл {file_path} не найден")
            continue
        
        file_size = Path(file_path).stat().st_size
        print(f"📄 Тестирую {doc_type}: {doc_info['description']}")
        print(f"   Размер: {file_size:,} байт")
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(file_path, "rb") as f:
                    files = {"files": (Path(file_path).name, f, doc_info["mime"])}
                    data = {
                        "message": f"Проанализируй этот {doc_type} документ: {doc_info['description']}. Выдели ключевые моменты и структуру.",
                        "agent": "agno_assist"
                    }
                    
                    response = await client.post(
                        f"{base_url}/v1/agents/agno_assist/runs",
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("content", "")
                        
                        print(f"✅ {doc_type}: Успешно обработан")
                        print(f"   Длина ответа: {len(content):,} символов")
                        
                        # Показываем начало ответа
                        preview = content[:300].replace('\n', ' ')
                        print(f"   Предпросмотр: {preview}...")
                        
                        # Проверяем наличие ключевых индикаторов успешной обработки
                        if any(keyword in content.lower() for keyword in ['документ', 'содержимое', 'анализ', 'структура']):
                            print(f"   🎯 Документ обработан корректно")
                        else:
                            print(f"   ⚠️  Возможно, документ обработан некорректно")
                        
                        print()
                    else:
                        print(f"❌ {doc_type}: Ошибка {response.status_code}")
                        error_text = response.text[:200]
                        print(f"   Ошибка: {error_text}")
                        print()
                        
        except Exception as e:
            print(f"❌ {doc_type}: Исключение - {e}")
            print()
    
    # Тест через JSON API с base64
    print("\n📤 Тестирование через JSON API\n")
    
    for doc_type, doc_info in test_files.items():
        file_path = doc_info["path"]
        
        if not Path(file_path).exists():
            continue
        
        file_size = Path(file_path).stat().st_size
        print(f"📄 Тестирую {doc_type} через JSON: {doc_info['description']}")
        print(f"   Размер: {file_size:,} байт")
            
        try:
            # Читаем файл и кодируем в base64
            with open(file_path, "rb") as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                "message": f"Проанализируй этот {doc_type} документ через JSON API. Извлеки основные данные и структуру.",
                "agent": "agno_assist",
                "files": [{
                    "filename": Path(file_path).name,
                    "content": file_content,
                    "mime_type": doc_info["mime"]
                }]
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/v1/agents/agno_assist/runs",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("content", "")
                    
                    print(f"✅ {doc_type}: Успешно обработан через JSON")
                    print(f"   Длина ответа: {len(content):,} символов")
                    
                    # Показываем начало ответа
                    preview = content[:300].replace('\n', ' ')
                    print(f"   Предпросмотр: {preview}...")
                    
                    # Анализируем качество обработки
                    quality_indicators = [
                        ('📊 Таблицы', any(word in content.lower() for word in ['таблица', 'лист', 'строк', 'столбец'])),
                        ('📝 Текст', any(word in content.lower() for word in ['текст', 'содержимое', 'параграф'])),
                        ('🔢 Данные', any(word in content.lower() for word in ['данные', 'значение', 'информация'])),
                        ('📋 Структура', any(word in content.lower() for word in ['структура', 'разделы', 'слайд']))
                    ]
                    
                    found_indicators = [ind for ind, found in quality_indicators if found]
                    if found_indicators:
                        print(f"   🎯 Обнаружено: {', '.join(found_indicators)}")
                    
                    print()
                else:
                    print(f"❌ {doc_type}: Ошибка {response.status_code}")
                    error_text = response.text[:200]
                    print(f"   Ошибка: {error_text}")
                    print()
                    
        except Exception as e:
            print(f"❌ {doc_type}: Исключение - {e}")
            print()

    print("\n🏁 Тестирование завершено!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_document_support()) 