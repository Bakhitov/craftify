import warnings
# Игнорируем предупреждение pydub о ffmpeg - мы используем OpenAI Whisper для аудио
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from logging import getLogger

from api.routes.v1_router import v1_router
from api.settings import api_settings
from agents.patches import apply_agno_patches

# Применяем патчи для Agno при запуске
apply_agno_patches()

logger = getLogger(__name__)


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
    )

    # Add v1 router
    app.include_router(v1_router)

    # Add Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create a FastAPI app
app = create_app()
