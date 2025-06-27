#!/usr/bin/env python3
"""
Скрипт для диагностики проблемы с AudioArtifact в базе данных.
"""

from db.session import SessionLocal
from sqlalchemy import text
import json

def check_audio_artifacts():
    """Проверяет записи с аудио данными в базе"""
    print("🔍 Проверка аудио артефактов в базе данных...")
    
    with SessionLocal() as session:
        # Ищем все записи с аудио данными
        query = text("""
            SELECT session_id, agent_data 
            FROM sessions 
            WHERE agent_data IS NOT NULL 
            AND agent_data::text LIKE '%audio%'
            LIMIT 5
        """)
        
        results = session.execute(query).fetchall()
        
        print(f"Найдено {len(results)} записей с аудио данными")
        
        for session_id, agent_data in results:
            print(f"\n📝 Session: {session_id}")
            
            if isinstance(agent_data, dict) and 'audio' in agent_data:
                audio_data = agent_data['audio']
                print(f"   Аудио записей: {len(audio_data) if isinstance(audio_data, list) else 1}")
                
                # Проверяем структуру первой аудио записи
                if isinstance(audio_data, list) and audio_data:
                    first_audio = audio_data[0]
                    print(f"   Структура первой записи: {list(first_audio.keys()) if isinstance(first_audio, dict) else 'Неизвестная'}")
                    
                    # Проверяем наличие обязательных полей
                    if isinstance(first_audio, dict):
                        has_url = 'url' in first_audio and first_audio['url']
                        has_base64 = 'base64_audio' in first_audio and first_audio['base64_audio']
                        print(f"   ✅ URL: {has_url}")
                        print(f"   ✅ Base64: {has_base64}")
                        
                        if not has_url and not has_base64:
                            print(f"   ❌ ПРОБЛЕМА: Отсутствуют url и base64_audio!")
                            print(f"   📋 Полная запись: {json.dumps(first_audio, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    check_audio_artifacts() 