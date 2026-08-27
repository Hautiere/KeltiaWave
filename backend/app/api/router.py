from fastapi import APIRouter

from app.api.routes.transcription_models import router as models_router
from app.record.routes import router as record_router
from app.subtitles.routes import router as subtitles_router
from app.transcribe.routes import router as transcribe_router

api_router = APIRouter()
api_router.include_router(models_router)
api_router.include_router(transcribe_router)
api_router.include_router(record_router)
api_router.include_router(subtitles_router)
