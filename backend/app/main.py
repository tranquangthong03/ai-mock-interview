from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, check_and_reset_database
from app.models import Document, InterviewSession, InterviewMessage, AnswerEvaluation, InterviewReport  # noqa: F401 - ensure models are registered before create_all
from app.routers import documents, rag, interviews, reports
from app.services.audio_processing_service import _get_stt_mode, is_ffmpeg_available

check_and_reset_database()

app = FastAPI(
    title="AI Mock Interviewer API",
    description="Backend API for AI Mock Interviewer project",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(interviews.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "message": "AI Mock Interviewer Backend is running",
        "stt_provider": _get_stt_mode(),
        "ffmpeg_available": is_ffmpeg_available(),
    }
