"""
Fix audio artifacts with missing required fields

Revision ID: 005_fix_audio_artifacts
Revises: 004_add_storage_config
Create Date: 2024-12-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '005_fix_audio_artifacts'
down_revision = '004_add_storage_config'
branch_labels = None
depends_on = None

def upgrade():
    """Исправляем аудио артефакты с отсутствующими обязательными полями"""
    
    # Создаем функцию для очистки некорректных аудио записей
    op.execute("""
        CREATE OR REPLACE FUNCTION fix_audio_artifacts()
        RETURNS void AS $$
        DECLARE
            session_record RECORD;
            audio_record JSONB;
            fixed_audio JSONB := '[]'::jsonb;
            needs_update BOOLEAN := false;
        BEGIN
            -- Перебираем все сессии с аудио данными
            FOR session_record IN 
                SELECT session_id, agent_data 
                FROM sessions 
                WHERE agent_data IS NOT NULL 
                AND agent_data ? 'audio'
                AND jsonb_array_length(agent_data->'audio') > 0
            LOOP
                fixed_audio := '[]'::jsonb;
                needs_update := false;
                
                -- Проверяем каждую аудио запись
                FOR audio_record IN 
                    SELECT * FROM jsonb_array_elements(session_record.agent_data->'audio')
                LOOP
                    -- Проверяем наличие обязательных полей
                    IF audio_record ? 'url' AND audio_record->>'url' IS NOT NULL AND audio_record->>'url' != '' THEN
                        -- URL есть - запись корректна
                        fixed_audio := fixed_audio || audio_record;
                    ELSIF audio_record ? 'base64_audio' AND audio_record->>'base64_audio' IS NOT NULL AND audio_record->>'base64_audio' != '' THEN
                        -- Base64 есть - запись корректна  
                        fixed_audio := fixed_audio || audio_record;
                    ELSE
                        -- Некорректная запись - пропускаем и помечаем что нужно обновление
                        needs_update := true;
                        RAISE NOTICE 'Removing invalid audio artifact from session %: %', session_record.session_id, audio_record;
                    END IF;
                END LOOP;
                
                -- Обновляем сессию если были изменения
                IF needs_update THEN
                    UPDATE sessions 
                    SET agent_data = jsonb_set(
                        session_record.agent_data,
                        '{audio}',
                        fixed_audio
                    )
                    WHERE session_id = session_record.session_id;
                    
                    RAISE NOTICE 'Fixed audio artifacts in session %', session_record.session_id;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Запускаем исправление
    op.execute("SELECT fix_audio_artifacts();")
    
    # Удаляем временную функцию
    op.execute("DROP FUNCTION fix_audio_artifacts();")

def downgrade():
    """Эта миграция необратима - мы не можем восстановить некорректные данные"""
    pass
