from enum import Enum
from logging import getLogger
from typing import AsyncGenerator, List, Optional, Union
from datetime import datetime

from agno.agent import Agent, AgentKnowledge
from agno.storage.session.agent import AgentSession
from agno.media import File, Image, Audio, Video
from fastapi import APIRouter, HTTPException, status, UploadFile, File as FastAPIFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.static.agno_assist import get_agno_assist_knowledge
from agents.selector import get_agent, get_available_agents, get_static_agent_details, is_static_agent, get_static_agents
from agents.models.saas_models import StaticAgentResponse
from db.session import SessionLocal
from sqlalchemy import text
from agents.cache import cache_manager

logger = getLogger(__name__)

######################################################
## Routes for the Agent Interface
######################################################

agents_router = APIRouter(prefix="/agents", tags=["Agents"])


class Model(str, Enum):
    gpt_4_1 = "gpt-4.1"
    o4_mini = "o4-mini"


@agents_router.get("", response_model=List[Union[StaticAgentResponse, dict]])
async def list_agents():
    """
    Returns a list of all available agents with full information.
    Static agents return StaticAgentResponse format, dynamic agents return dict format.
    OPTIMIZED: Uses bulk operations to avoid N+1 queries, but respects cache for auto-updates.

    Returns:
        List[Union[StaticAgentResponse, dict]]: List of agent information
    """
    from agents.cache import cache_manager
    
    # Проверяем кэш для полного списка агентов
    cache_key = "agents:full_list"
    cached_agents = cache_manager.get(cache_key)
    if cached_agents:
        logger.info(f"Returned {len(cached_agents)} agents from cache")
        return cached_agents
    
    agents_info = []
    
    try:
        # 1. Получаем все статические агенты (быстрая операция)
        static_agent_ids = get_static_agents()
        
        # 2. Получаем всех динамических агентов одним запросом (вместо N запросов)
        dynamic_agents_bulk = []
        try:
            with SessionLocal() as session:
                query = text("""
                    SELECT id, name, agent_id, description, instructions,
                           model_config, tools_config, knowledge_config,
                           memory_config, storage_config, settings, is_active, 
                           created_at, updated_at
                    FROM dynamic_agents
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """)
                
                result = session.execute(query)
                for row in result.fetchall():
                    # Извлекаем model_id из model_config
                    model_config = row.model_config if row.model_config else {}
                    model_id = model_config.get("id", "gpt-4o-mini")
                    
                    dynamic_agent_info = {
                        "id": row.id,
                        "name": row.name,
                        "agent_id": row.agent_id,
                        "description": row.description,
                        "instructions": row.instructions,
                        "model_id": model_id,
                        "model_config": model_config,
                        "tools_config": row.tools_config if row.tools_config else [],
                        "knowledge_config": row.knowledge_config if row.knowledge_config else {},
                        "memory_config": row.memory_config if row.memory_config else {},
                        "storage_config": row.storage_config if row.storage_config else {},
                        "settings": row.settings if row.settings else {},
                        "is_active": row.is_active,
                        "max_tokens": None,
                        "temperature": None,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None
                    }
                    dynamic_agents_bulk.append(dynamic_agent_info)
                    
        except Exception as db_error:
            logger.error(f"Database error while loading dynamic agents: {db_error}")
        
        # 3. Добавляем статические агенты (используем кэшированные детали)
        for agent_id in static_agent_ids:
            try:
                agent_details = get_static_agent_details(agent_id)
                static_agent = StaticAgentResponse(
                    id=None,
                    name=agent_details.get("name", agent_id),
                    agent_id=agent_id,
                    description=agent_details.get("description"),
                    instructions=agent_details.get("instructions"),
                    model_id=agent_details.get("model_id", "gpt-4.1"),
                    model_config_data=agent_details.get("model_config", {}),
                    tools_config=agent_details.get("tools_config", []),
                    knowledge_config=agent_details.get("knowledge_config", {}),
                    memory_config=agent_details.get("memory_config", {}),
                    storage_config=agent_details.get("storage_config", {}),
                    settings=agent_details.get("settings", {}),
                    is_active=agent_details.get("is_active", True),
                    max_tokens=agent_details.get("max_tokens"),
                    temperature=agent_details.get("temperature"),
                    created_at=None,
                    updated_at=None,
                    agent_type="static",
                    source_file=agent_details.get("source_file"),
                    editable=False
                )
                agents_info.append(static_agent.model_dump(by_alias=True))
            except Exception as e:
                logger.warning(f"Failed to get details for static agent {agent_id}: {e}")
                # Добавляем базовую информацию при ошибке
                agents_info.append({
                    "agent_id": agent_id,
                    "type": "static",
                    "name": agent_id,
                    "error": str(e)
                })
        
        # 4. Добавляем все динамические агенты (уже загружены bulk операцией)
        agents_info.extend(dynamic_agents_bulk)
        
        # 5. Кэшируем результат на 5 минут (с поддержкой автообновления)
        cache_manager.set(cache_key, agents_info, ttl=300)
        
        logger.info(f"Loaded {len(static_agent_ids)} static and {len(dynamic_agents_bulk)} dynamic agents")
        
    except Exception as e:
        logger.error(f"Error in list_agents: {e}")
        # В случае критической ошибки возвращаем хотя бы базовый список
        return [{
            "error": "Failed to load agents",
            "message": str(e)
        }]
    
    return agents_info


async def chat_response_streamer(
    agent: Agent, 
    message: str, 
    files: Optional[List[File]] = None,
    images: Optional[List[Image]] = None,
    audio: Optional[List[Audio]] = None,
    videos: Optional[List[Video]] = None
) -> AsyncGenerator:
    """
    Stream agent responses chunk by chunk.

    Args:
        agent: The agent instance to interact with
        message: User message to process
        files: Optional list of files to process
        images: Optional list of images to process
        audio: Optional list of audio to process
        videos: Optional list of videos to process

    Yields:
        Text chunks from the agent response
    """
    run_response = await agent.arun(
        message, 
        stream=True,
        files=files,
        images=images,
        audio=audio,
        videos=videos
    )
    async for chunk in run_response:
        # chunk.content only contains the text response from the Agent.
        # For advanced use cases, we should yield the entire chunk
        # that contains the tool calls and intermediate steps.
        yield chunk.content


async def process_uploaded_files(
    files: Optional[List[UploadFile]] = None,
    images: Optional[List[UploadFile]] = None,
    audio: Optional[List[UploadFile]] = None,
    videos: Optional[List[UploadFile]] = None
) -> tuple[Optional[List[File]], Optional[List[Image]], Optional[List[Audio]], Optional[List[Video]], str]:
    """
    Обрабатывает загруженные файлы и конвертирует их в объекты Agno Media.
    Полная совместимость с Agno Agent arun() методом.

    Args:
        files: Загруженные файлы (документы, код, текст)
        images: Загруженные изображения 
        audio: Загруженные аудио файлы
        videos: Загруженные видео файлы

    Returns:
        Кортеж: (files, images, audio, videos, text_content_summary)
    """
    processed_files = []
    processed_images = []
    processed_audio = []
    processed_videos = []
    text_content_summary = ""

    # Поддерживаемые MIME типы для файлов в OpenAI (только PDF)
    OPENAI_SUPPORTED_FILE_TYPES = {"application/pdf"}

    def determine_file_mime_type(upload_file: UploadFile) -> str:
        """Определяет MIME тип файла на основе content_type и расширения"""
        content_type = upload_file.content_type
        filename = upload_file.filename or ""
        
        # Если MIME тип уже поддерживается OpenAI, используем его
        if content_type and content_type in OPENAI_SUPPORTED_FILE_TYPES:
            return content_type
            
        # Иначе определяем по расширению файла
        if filename and '.' in filename:
            ext = filename.lower().split('.')[-1]
            if ext == 'pdf':
                return 'application/pdf'
        
        # Для остальных типов возвращаем None (будем обрабатывать как текст)
        return None

    def is_text_file(filename: str, content_type: str) -> bool:
        """Проверяет, является ли файл текстовым"""
        if not filename:
            return False
        
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        text_extensions = {
            'txt', 'md', 'markdown', 'py', 'js', 'html', 'htm', 'css', 
            'json', 'xml', 'yaml', 'yml', 'csv', 'rtf', 'log'
        }
        
        return ext in text_extensions or (content_type and content_type.startswith('text/'))

    # Обрабатываем файлы (документы, код, текст)
    if files:
        text_files_content = []
        
        for upload_file in files:
            try:
                content = await upload_file.read()
                filename = upload_file.filename or "unknown_file"
                mime_type = determine_file_mime_type(upload_file)
                
                # Если это PDF - обрабатываем как File объект для OpenAI
                if mime_type == "application/pdf":
                    import base64
                    encoded_content = base64.b64encode(content).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{encoded_content}"
                    
                    agno_file = File(
                        content=data_url,
                        mime_type=mime_type
                    )
                    processed_files.append(agno_file)
                    logger.info(f"Processed PDF file: {filename}, size: {len(content)} bytes")
                
                # Если это текстовый файл - добавляем содержимое в сообщение
                elif is_text_file(filename, upload_file.content_type or ""):
                    try:
                        # Пытаемся декодировать как текст
                        text_content = content.decode('utf-8', errors='replace')
                        text_files_content.append(f"""
📄 **Файл: {filename}**
```
{text_content}
```
""")
                        logger.info(f"Processed text file: {filename}, size: {len(content)} bytes")
                    except Exception as decode_error:
                        logger.warning(f"Could not decode {filename} as text: {decode_error}")
                        text_files_content.append(f"📄 **Файл: {filename}** - Не удалось прочитать содержимое")
                
                else:
                    # Неподдерживаемый тип файла
                    logger.warning(f"Unsupported file type: {filename} ({upload_file.content_type})")
                    text_files_content.append(f"📄 **Файл: {filename}** - Неподдерживаемый тип файла")
                
            except Exception as e:
                logger.error(f"Error processing file {upload_file.filename}: {e}")
                continue
        
        # Объединяем содержимое текстовых файлов
        if text_files_content:
            text_content_summary = "\n".join(text_files_content)

    # Обрабатываем изображения
    if images:
        for upload_file in images:
            try:
                content = await upload_file.read()
                
                # Определяем формат по расширению
                format_type = None
                if upload_file.filename and '.' in upload_file.filename:
                    format_type = upload_file.filename.split('.')[-1].lower()
                
                # Создаем Agno Image объект
                agno_image = Image(
                    content=content,  # Agno ожидает raw bytes для изображений
                    format=format_type,
                    detail="auto"  # Для максимального качества анализа
                )
                processed_images.append(agno_image)
                
                logger.info(f"Processed image: {upload_file.filename}, size: {len(content)} bytes, format: {format_type}")
                
            except Exception as e:
                logger.error(f"Error processing image {upload_file.filename}: {e}")
                continue

    # Обрабатываем аудио файлы
    if audio:
        for upload_file in audio:
            try:
                content = await upload_file.read()
                
                # Определяем формат по расширению
                format_type = None
                if upload_file.filename and '.' in upload_file.filename:
                    format_type = upload_file.filename.split('.')[-1].lower()
                
                # Создаем Agno Audio объект
                agno_audio = Audio(
                    content=content,  # Agno ожидает raw bytes
                    format=format_type
                )
                processed_audio.append(agno_audio)
                
                logger.info(f"Processed audio: {upload_file.filename}, size: {len(content)} bytes, format: {format_type}")
                
            except Exception as e:
                logger.error(f"Error processing audio {upload_file.filename}: {e}")
                continue

    # Обрабатываем видео файлы
    if videos:
        for upload_file in videos:
            try:
                content = await upload_file.read()
                
                # Определяем формат по расширению
                format_type = None
                if upload_file.filename and '.' in upload_file.filename:
                    format_type = upload_file.filename.split('.')[-1].lower()
                
                # Создаем Agno Video объект
                agno_video = Video(
                    content=content,  # Agno ожидает raw bytes
                    format=format_type
                )
                processed_videos.append(agno_video)
                
                logger.info(f"Processed video: {upload_file.filename}, size: {len(content)} bytes, format: {format_type}")
                
            except Exception as e:
                logger.error(f"Error processing video {upload_file.filename}: {e}")
                continue

    return (
        processed_files if processed_files else None,
        processed_images if processed_images else None,
        processed_audio if processed_audio else None,
        processed_videos if processed_videos else None,
        text_content_summary
    )


class RunRequest(BaseModel):
    """Request model for an running an agent"""

    message: str
    stream: bool = False
    model: Model = Model.gpt_4_1
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@agents_router.post("/{agent_id}/runs", status_code=status.HTTP_200_OK)
async def create_agent_run(agent_id: str, body: RunRequest):
    """
    Sends a message to a specific agent and returns the response.

    Args:
        agent_id: The ID of the agent to interact with
        body: Request parameters including the message

    Returns:
        Either a streaming response or the complete agent response
    """
    logger.debug(f"RunRequest: {body}")

    try:
        agent: Agent = get_agent(
            agent_id=agent_id,
            model_id=body.model.value,
            user_id=body.user_id,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if body.stream:
        return StreamingResponse(
            chat_response_streamer(agent, body.message),
            media_type="text/event-stream",
        )
    else:
        response = await agent.arun(body.message, stream=False)
        # Возвращаем полный RunResponse с поддержкой мультимедиа артефактов
        # для максимальной совместимости с возможностями Agno агентов
        return {
            "content": response.content,
            "content_type": response.content_type,
            "images": [img.to_dict() for img in response.images] if response.images else None,
            "videos": [vid.to_dict() for vid in response.videos] if response.videos else None, 
            "audio": [aud.to_dict() for aud in response.audio] if response.audio else None,
            "response_audio": response.response_audio.to_dict() if response.response_audio else None,
            "citations": response.citations.model_dump() if response.citations else None,
            "thinking": response.thinking,
            "reasoning_content": response.reasoning_content,
            "metrics": response.metrics,
            "model": response.model,
            "run_id": response.run_id,
            "session_id": response.session_id,
            "formatted_tool_calls": response.formatted_tool_calls
        }


@agents_router.post("/{agent_id}/runs/multipart", status_code=status.HTTP_200_OK)
async def create_agent_run_with_files(
    agent_id: str,
    message: str = Form(..., description="Текстовое сообщение для агента"),
    stream: bool = Form(False, description="Включить потоковый ответ"),
    model: str = Form("gpt-4.1", description="Модель для использования"),
    user_id: Optional[str] = Form(None, description="ID пользователя"),
    session_id: Optional[str] = Form(None, description="ID сессии"),
    files: Optional[List[UploadFile]] = FastAPIFile(None, description="Файлы для обработки (PDF, текст, код и др.)"),
    images: Optional[List[UploadFile]] = FastAPIFile(None, description="Изображения для анализа"),
    audio: Optional[List[UploadFile]] = FastAPIFile(None, description="Аудио файлы для обработки"),
    videos: Optional[List[UploadFile]] = FastAPIFile(None, description="Видео файлы для анализа"),
):
    """
    Отправляет сообщение с файлами агенту и возвращает ответ.
    Поддерживает multipart/form-data для загрузки мультимедиа контента.
    
    Мультимодальные возможности:
    - 📄 Файлы: PDF, текст, код, документы, JSON, YAML
    - 🖼️ Изображения: PNG, JPEG, WebP, GIF с высоким качеством анализа
    - 🎵 Аудио: различные аудио форматы
    - 🎬 Видео: MP4, MOV, AVI и другие
    
    Совместимость: Полная интеграция с Agno Agent.arun() API

    Args:
        agent_id: ID агента для взаимодействия
        message: Текстовое сообщение 
        stream: Включить потоковый ответ
        model: Модель для использования (gpt-4.1, o4-mini)
        user_id: ID пользователя для персонализации
        session_id: ID сессии для контекста
        files: Файлы документов, кода, текста
        images: Изображения для визуального анализа
        audio: Аудио файлы для анализа звука
        videos: Видео файлы для анализа видеоконтента

    Returns:
        Ответ агента (потоковый или обычный) с обработкой медиа контента
    """
    # Валидация входных данных
    if not message or not message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    # Подсчет общего количества файлов
    total_files = 0
    if files:
        total_files += len(files)
    if images:
        total_files += len(images)
    if audio:
        total_files += len(audio)
    if videos:
        total_files += len(videos)

    # Лимит файлов для предотвращения злоупотреблений
    MAX_FILES = 20
    if total_files > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum allowed: {MAX_FILES}, provided: {total_files}"
        )

    logger.info(f"🚀 Agent run request: agent={agent_id}, message_len={len(message)}, "
                f"files={len(files) if files else 0}, images={len(images) if images else 0}, "
                f"audio={len(audio) if audio else 0}, videos={len(videos) if videos else 0}")

    try:
        # Валидация модели
        SUPPORTED_MODELS = ["gpt-4.1", "o4-mini"]
        if model not in SUPPORTED_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Unsupported model: {model}. Supported: {SUPPORTED_MODELS}"
            )

        # Получаем агента
        agent: Agent = get_agent(
            agent_id=agent_id,
            model_id=model,
            user_id=user_id,
            session_id=session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        # Обрабатываем загруженные файлы с максимальной совместимостью с Agno
        processed_files, processed_images, processed_audio, processed_videos, text_content_summary = await process_uploaded_files(
            files=files,
            images=images, 
            audio=audio,
            videos=videos
        )

        # Логируем успешную обработку медиа контента
        media_summary = []
        if processed_files:
            media_summary.append(f"📄 {len(processed_files)} files")
        if processed_images:
            media_summary.append(f"🖼️ {len(processed_images)} images")
        if processed_audio:
            media_summary.append(f"🎵 {len(processed_audio)} audio")
        if processed_videos:
            media_summary.append(f"🎬 {len(processed_videos)} videos")
        
        if media_summary:
            logger.info(f"✅ Processed media for agent {agent_id}: {', '.join(media_summary)}")

        # Если есть текстовое содержимое файлов, добавляем его к сообщению
        enhanced_message = message
        if text_content_summary:
            enhanced_message = f"{message}\n\n📁 **Содержимое загруженных файлов:**\n{text_content_summary}"

        # Запускаем агента с полным мультимодальным контентом
        if stream:
            return StreamingResponse(
                chat_response_streamer(
                    agent, 
                    enhanced_message, 
                    files=processed_files,
                    images=processed_images,
                    audio=processed_audio,
                    videos=processed_videos
                ),
                media_type="text/event-stream",
            )
        else:
            response = await agent.arun(
                enhanced_message, 
                stream=False,
                files=processed_files,
                images=processed_images,
                audio=processed_audio,
                videos=processed_videos
            )
            # Возвращаем полный RunResponse с поддержкой мультимедиа артефактов
            # вместо только текстового содержимого для максимальной функциональности
            return {
                "content": response.content,
                "content_type": response.content_type,
                "images": [img.to_dict() for img in response.images] if response.images else None,
                "videos": [vid.to_dict() for vid in response.videos] if response.videos else None, 
                "audio": [aud.to_dict() for aud in response.audio] if response.audio else None,
                "response_audio": response.response_audio.to_dict() if response.response_audio else None,
                "citations": response.citations.model_dump() if response.citations else None,
                "thinking": response.thinking,
                "reasoning_content": response.reasoning_content,
                "metrics": response.metrics,
                "model": response.model,
                "run_id": response.run_id,
                "session_id": response.session_id,
                "formatted_tool_calls": response.formatted_tool_calls
            }

    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except Exception as e:
        logger.error(f"❌ Error in multimodal agent run for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process multimodal request: {str(e)}"
        )


@agents_router.get("/{agent_id}/sessions", status_code=status.HTTP_200_OK)
async def get_agent_sessions(agent_id: str, user_id: Optional[str] = None):
    """
    Получение сессий для конкретного агента.
    Аналогично native Agno endpoint AGENT_SESSION_CREATE.

    Args:
        agent_id: ID агента для получения сессий
        user_id: Опциональный ID пользователя для фильтрации

    Returns:
        Список сессий агента с метаданными
    """
    try:
        # Проверяем существование агента
        agent: Agent = get_agent(agent_id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        # Получаем сессии из storage если он настроен
        sessions = []
        if hasattr(agent, 'storage') and agent.storage:
            try:
                # Пытаемся получить сессии из storage
                # В Agno storage обычно содержит методы для работы с сессиями
                if hasattr(agent.storage, 'get_sessions'):
                    sessions_data = agent.storage.get_sessions(
                        agent_id=agent_id, 
                        user_id=user_id
                    )
                    if sessions_data:
                        sessions = [
                            {
                                "session_id": session.session_id,
                                "user_id": session.user_id,
                                "agent_id": session.agent_id,
                                "created_at": session.created_at,
                                "updated_at": session.updated_at,
                                "session_data": session.session_data,
                                "agent_data": session.agent_data
                            }
                            for session in sessions_data
                            if isinstance(session, AgentSession)
                        ]
            except Exception as e:
                logger.warning(f"Could not retrieve sessions from storage: {e}")
                # Если не удается получить из storage, возвращаем пустой список

        # Возвращаем ответ в формате совместимом с Agno
        return {
            "agent_id": agent_id,
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "agent_type": "static" if hasattr(agent, 'agent_id') else "dynamic",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving sessions for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions for agent {agent_id}"
        )


@agents_router.post("/{agent_id}/knowledge/load", status_code=status.HTTP_200_OK)
async def load_agent_knowledge(agent_id: str):
    """
    Loads the knowledge base for a specific agent.

    Args:
        agent_id: The ID of the agent to load knowledge for.

    Returns:
        A success message if the knowledge base is loaded.
    """
    agent_knowledge: Optional[AgentKnowledge] = None

    if agent_id == "agno_assist":
        agent_knowledge = get_agno_assist_knowledge()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent {agent_id} does not have a knowledge base.",
        )

    try:
        await agent_knowledge.aload(upsert=True)
    except Exception as e:
        logger.error(f"Error loading knowledge base for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load knowledge base for {agent_id}.",
        )

    return {"message": f"Knowledge base for {agent_id} loaded successfully."}
