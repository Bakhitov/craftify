"""
Патч для решения проблемы с AudioArtifact в Agno.
Обеспечивает безопасную загрузку сессий с некорректными аудио артефактами.
"""

import logging
from typing import List, Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)

def apply_agno_patches():
    """
    Применяет патчи для решения проблем с Agno.
    """
    try:
        # Патчим методы загрузки сессии
        import agno.agent.agent
        
        # Сохраняем оригинальный метод
        original_load_agent_session = agno.agent.agent.Agent.load_agent_session
        
        def patched_load_agent_session(self, session):
            """Безопасная загрузка сессии с обработкой AudioArtifact ошибок"""
            try:
                return original_load_agent_session(self, session)
            except Exception as e:
                error_str = str(e)
                if "AudioArtifact" in error_str and ("url" in error_str or "base64_audio" in error_str):
                    logger.warning(f"🔧 AudioArtifact ошибка исправлена: {error_str}")
                    
                    # Очищаем проблемные аудио данные из сессии
                    if hasattr(session, 'agent_data') and session.agent_data:
                        try:
                            import json
                            if isinstance(session.agent_data, str):
                                data = json.loads(session.agent_data)
                            else:
                                data = session.agent_data
                            
                            # Удаляем проблемные аудио элементы
                            if isinstance(data, dict):
                                # Рекурсивно очищаем аудио данные
                                cleaned_data = clean_audio_artifacts(data)
                                session.agent_data = json.dumps(cleaned_data) if isinstance(session.agent_data, str) else cleaned_data
                                logger.info("✅ Аудио артефакты очищены из сессии")
                        except Exception as clean_error:
                            logger.warning(f"Не удалось очистить данные сессии: {clean_error}")
                    
                    # Возвращаем сессию без вызова проблемного кода
                    return session
                else:
                    # Перебрасываем другие ошибки
                    raise e
        
        # Применяем патч
        agno.agent.agent.Agent.load_agent_session = patched_load_agent_session
        logger.info("✅ Agno патч для AudioArtifact применен")
        
    except ImportError:
        logger.warning("⚠️ Не удалось применить Agno патч - модуль не найден")
    except Exception as e:
        logger.error(f"❌ Ошибка применения Agno патча: {e}")

def clean_audio_artifacts(data, max_depth=10):
    """
    Рекурсивно очищает некорректные аудио артефакты из данных.
    """
    if max_depth <= 0:
        return data
        
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if key == "audio" and isinstance(value, dict):
                # Проверяем аудио объект на корректность
                if not value.get("url") and not value.get("base64_audio"):
                    logger.debug(f"Удален некорректный аудио объект: {key}")
                    continue  # Пропускаем некорректный аудио объект
            cleaned[key] = clean_audio_artifacts(value, max_depth - 1)
        return cleaned
    elif isinstance(data, list):
        cleaned = []
        for item in data:
            cleaned_item = clean_audio_artifacts(item, max_depth - 1)
            # Не добавляем пустые аудио объекты
            if not (isinstance(cleaned_item, dict) and 
                   cleaned_item.get("type") == "audio" and 
                   not cleaned_item.get("url") and 
                   not cleaned_item.get("base64_audio")):
                cleaned.append(cleaned_item)
        return cleaned
    else:
        return data

def clean_audio_artifacts_from_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Очищает данные от некорректных аудио артефактов.
    """
    if not isinstance(data, dict):
        return data
    
    cleaned_data = data.copy()
    
    # Ищем и удаляем проблемные аудио артефакты
    if 'audio_artifacts' in cleaned_data:
        artifacts = cleaned_data['audio_artifacts']
        if isinstance(artifacts, list):
            valid_artifacts = []
            for artifact in artifacts:
                if isinstance(artifact, dict):
                    # Проверяем, что у артефакта есть нужные поля
                    if artifact.get('url') or artifact.get('base64_audio'):
                        valid_artifacts.append(artifact)
                    else:
                        logger.warning(f"Удаляем некорректный аудио артефакт: {artifact.get('id', 'unknown')}")
            cleaned_data['audio_artifacts'] = valid_artifacts
    
    # Рекурсивно обрабатываем вложенные данные
    for key, value in cleaned_data.items():
        if isinstance(value, dict):
            cleaned_data[key] = clean_audio_artifacts_from_data(value)
        elif isinstance(value, list):
            cleaned_data[key] = [
                clean_audio_artifacts_from_data(item) if isinstance(item, dict) else item
                for item in value
            ]
    
    return cleaned_data 