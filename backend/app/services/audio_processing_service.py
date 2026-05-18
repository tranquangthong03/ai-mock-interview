"""
Audio Processing Service

Handles:
  - Saving uploaded audio files
  - Transcribing audio to text via mock, openai-whisper, or faster-whisper
  - Computing basic speech metrics from transcript
"""

import logging
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from app.services.language_policy import STT_LANGUAGE


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AUDIO_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "audio"
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".ogg"}
FFMPEG_REQUIRED_MESSAGE = (
    "FFmpeg is required for audio transcription but was not found. "
    "Please install FFmpeg and add it to PATH. On Windows, run: "
    "winget install Gyan.FFmpeg, then close and reopen your terminal or VS Code."
)
WHISPER_INITIAL_PROMPT = (
    "This is an English technical interview answer about software engineering, "
    "AI, machine learning, backend, frontend, databases, and project experience."
)

# Filler words to detect. English fillers are primary for the new interview
# flow; Vietnamese variants are kept so mixed-language answers still get notes.
FILLER_PATTERNS = [
    r"\bo\b",
    r"\ba\b",
    r"\bum\b",
    r"\buh\b",
    r"\buhm\b",
    r"\blike\b",
    r"\byou know\b",
    r"\bactually\b",
    r"\bbasically\b",
    r"\bso\b",
    r"\bwell\b",
    r"\bthi\b",
    r"\bkieu nhu\b",
    r"\bnoi chung\b",
    r"\bnoi chung la\b",
    r"\bờ\b",
    r"\bà\b",
    r"\bừm\b",
    r"\bừ\b",
    r"\bthì\b",
    r"\bkiểu như\b",
    r"\bnói chung\b",
    r"\bnói chung là\b",
]

# Average interview speech rate is often ~130-160 wpm; use 140 as a default estimator.
DEFAULT_SPEECH_RATE_WPM = 140


class AudioProcessingError(Exception):
    """Expected audio/STT failure that should be returned clearly to clients."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# STT Provider abstraction
# ---------------------------------------------------------------------------

def _get_stt_mode() -> str:
    """Return 'whisper', 'faster-whisper', or 'mock' based on env."""
    return os.environ.get("STT_PROVIDER", "mock").strip().lower()


def _get_stt_language() -> str:
    """Return the STT target language from env, default English."""
    return os.environ.get("STT_LANGUAGE", STT_LANGUAGE).strip().lower()


def _get_whisper_model_name() -> str:
    """Return configured Whisper model, preferring English-only defaults."""
    return (
        os.environ.get("WHISPER_MODEL")
        or os.environ.get("WHISPER_MODEL_SIZE")
        or "base.en"
    ).strip()


def is_ffmpeg_available() -> bool:
    """Return True when ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def require_ffmpeg_for_real_stt(provider: str) -> None:
    """Fail early with an actionable message before whisper calls ffmpeg."""
    if provider in {"whisper", "faster-whisper"} and not is_ffmpeg_available():
        logger.error(
            "[Audio/STT] ffmpeg not found for STT_PROVIDER=%s. Install with: winget install Gyan.FFmpeg",
            provider,
        )
        raise AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503)


def convert_audio_to_wav_16k_mono(file_path: str | Path) -> Path:
    """
    Convert browser-recorded audio to a stable Whisper input format.

    MediaRecorder commonly uploads webm/opus. Whisper can call ffmpeg itself,
    but normalizing to wav mono 16 kHz avoids unstable format probing and makes
    the transcription input explicit.
    """
    source = Path(file_path)
    if not source.exists():
        raise AudioProcessingError(f"Audio file does not exist: {source}", status_code=400)
    if source.stat().st_size <= 0:
        raise AudioProcessingError("Uploaded audio file is empty. Please record again.", status_code=400)

    if not is_ffmpeg_available():
        logger.error("[Audio/STT] ffmpeg not found before audio conversion path=%s", source)
        raise AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503)

    if source.suffix.lower() == ".wav":
        output = source.with_name(f"{source.stem}_16k_mono.wav")
    else:
        output = source.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output),
    ]
    logger.info("[Audio/STT] Converting audio to wav16k_mono input=%s output=%s", source, output)
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        logger.exception("[Audio/STT] ffmpeg executable disappeared during conversion.")
        raise AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503) from e

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        logger.error("[Audio/STT] ffmpeg conversion failed code=%s stderr=%s", completed.returncode, stderr[-1000:])
        raise AudioProcessingError(
            "Audio conversion failed. Please record again or try a different browser.",
            status_code=400,
        )

    if not output.exists() or output.stat().st_size <= 0:
        logger.error("[Audio/STT] ffmpeg conversion output missing/empty output=%s", output)
        raise AudioProcessingError(
            "Audio conversion produced an empty file. Please record again.",
            status_code=400,
        )

    logger.info("[Audio/STT] Converted audio output=%s size=%s", output, output.stat().st_size)
    return output


def transcribe_audio(file_path: str | Path) -> str:
    """
    Transcribe an audio file to text.

    Supports:
      - STT_PROVIDER=mock            -> placeholder transcript for dev/test
      - STT_PROVIDER=whisper         -> openai-whisper
      - STT_PROVIDER=faster-whisper  -> faster-whisper
    """
    mode = _get_stt_mode()
    language = _get_stt_language()
    model_name = _get_whisper_model_name()
    path = Path(file_path)

    logger.info(
        "[Audio/STT] Starting transcription provider=%s language=%s whisper_model=%s path=%s exists=%s size=%s ffmpeg_available=%s",
        mode,
        language,
        model_name,
        path,
        path.exists(),
        path.stat().st_size if path.exists() else "missing",
        is_ffmpeg_available(),
    )

    if not path.exists():
        raise AudioProcessingError(f"Audio file does not exist: {path}", status_code=400)
    if path.stat().st_size <= 0:
        raise AudioProcessingError("Uploaded audio file is empty. Please record again.", status_code=400)

    require_ffmpeg_for_real_stt(mode)

    if mode == "faster-whisper":
        transcript = _transcribe_faster_whisper(convert_audio_to_wav_16k_mono(path))
    elif mode == "whisper":
        transcript = _transcribe_whisper(convert_audio_to_wav_16k_mono(path))
    else:
        transcript = _transcribe_mock(path)

    logger.info("[Audio/STT] Transcript result provider=%s transcript=%s", mode, transcript)
    return transcript


def _transcribe_mock(file_path: str | Path) -> str:
    """Mock transcription for development/testing."""
    return (
        "I would optimize the CNN inference time by applying model pruning, "
        "quantization, batching, and measuring latency after each change."
    )


def _transcribe_faster_whisper(file_path: str | Path) -> str:
    """Transcribe using faster-whisper library."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise AudioProcessingError(
            "faster-whisper is not installed. Run: pip install faster-whisper or set STT_PROVIDER=mock.",
            status_code=503,
        ) from e

    model_size = _get_whisper_model_name()
    language = _get_stt_language()
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(
            str(file_path),
            language=language,
            task="transcribe",
            vad_filter=True,
            beam_size=5,
            initial_prompt=WHISPER_INITIAL_PROMPT,
        )
        text_parts = [segment.text for segment in segments]
        return " ".join(text_parts).strip()
    except FileNotFoundError as e:
        logger.exception("[Audio/STT] faster-whisper failed because a required executable/file was not found.")
        raise AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503) from e
    except Exception as e:
        logger.exception("[Audio/STT] faster-whisper transcription failed.")
        raise AudioProcessingError(f"Audio transcription failed: {e}", status_code=500) from e


def _transcribe_whisper(file_path: str | Path) -> str:
    """Transcribe using openai-whisper library."""
    try:
        import whisper
    except ImportError as e:
        raise AudioProcessingError(
            "openai-whisper is not installed. Run: pip install openai-whisper or set STT_PROVIDER=mock.",
            status_code=503,
        ) from e

    model_name = _get_whisper_model_name()
    language = _get_stt_language()
    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(
            str(file_path),
            language=language,
            task="transcribe",
            fp16=False,
            initial_prompt=WHISPER_INITIAL_PROMPT,
        )
        return result.get("text", "").strip()
    except FileNotFoundError as e:
        logger.exception("[Audio/STT] openai-whisper failed because a required executable/file was not found.")
        raise AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503) from e
    except Exception as e:
        logger.exception("[Audio/STT] openai-whisper transcription failed.")
        raise AudioProcessingError(f"Audio transcription failed: {e}", status_code=500) from e


# ---------------------------------------------------------------------------
# Speech Metrics
# ---------------------------------------------------------------------------

def compute_speech_metrics(
    transcript: str | None,
    audio_duration_seconds: float | None = None,
) -> dict:
    """
    Compute basic speech presentation metrics from a transcript.

    These are presentation indicators only, not assessments of confidence or
    competence.
    """
    if not transcript or not transcript.strip():
        return {
            "duration_seconds": 0,
            "word_count": 0,
            "speech_rate_wpm": 0,
            "filler_words": [],
            "filler_word_count": 0,
            "estimated_pause_count": 0,
            "notes": ["Transcript rong - khong the phan tich."],
        }

    words = transcript.strip().split()
    word_count = len(words)

    found_fillers: list[str] = []
    lower_text = transcript.lower()
    for pattern in FILLER_PATTERNS:
        matches = re.findall(pattern, lower_text)
        found_fillers.extend(matches)

    if audio_duration_seconds and audio_duration_seconds > 0:
        duration = audio_duration_seconds
        speech_rate_wpm = round((word_count / duration) * 60, 1) if duration > 0 else 0
    else:
        duration = round((word_count / DEFAULT_SPEECH_RATE_WPM) * 60, 1)
        speech_rate_wpm = DEFAULT_SPEECH_RATE_WPM

    pause_chars = transcript.count(".") + transcript.count(",") + transcript.count("...")
    estimated_pause_count = max(0, pause_chars - 1)

    notes: list[str] = []
    if speech_rate_wpm > 180:
        notes.append("Toc do noi kha nhanh - can nhac noi cham hon de ro rang hon.")
    elif speech_rate_wpm < 100 and word_count > 5:
        notes.append("Toc do noi kha cham - co the cai thien tinh troi chay.")
    if len(found_fillers) > 3:
        notes.append(f"Phat hien {len(found_fillers)} tu dem - thu giam de trinh bay mach lac hon.")

    return {
        "duration_seconds": round(duration, 1),
        "word_count": word_count,
        "speech_rate_wpm": round(speech_rate_wpm, 1),
        "filler_words": found_fillers,
        "filler_word_count": len(found_fillers),
        "estimated_pause_count": estimated_pause_count,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# File Management
# ---------------------------------------------------------------------------

def save_upload_audio_file(upload_file, session_id: int) -> str:
    """
    Save an uploaded audio file to disk.

    Returns the path to the saved file. Raises AudioProcessingError for expected
    validation/save failures.
    """
    original_name = getattr(upload_file, "filename", "audio.webm") or "audio.webm"
    content_type = getattr(upload_file, "content_type", "") or ""
    ext = Path(original_name).suffix.lower()

    logger.info(
        "[Audio/STT] Received upload session_id=%s filename=%s content_type=%s extension=%s provider=%s language=%s whisper_model=%s ffmpeg_available=%s",
        session_id,
        original_name,
        content_type,
        ext,
        _get_stt_mode(),
        _get_stt_language(),
        _get_whisper_model_name(),
        is_ffmpeg_available(),
    )

    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise AudioProcessingError(
            f"File extension '{ext}' is not supported. Accepted: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            status_code=400,
        )

    upload_dir = Path(AUDIO_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique = uuid.uuid4().hex[:8]
    safe_name = f"session_{session_id}_{timestamp}_{unique}{ext}"
    dest_path = upload_dir / safe_name

    content = upload_file.file.read()
    if not content:
        raise AudioProcessingError("Uploaded audio file is empty. Please record again.", status_code=400)

    with open(dest_path, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    if not dest_path.exists() or dest_path.stat().st_size <= 0:
        raise AudioProcessingError("Audio file was not saved correctly. Please record again.", status_code=500)

    logger.info(
        "[Audio/STT] Saved audio path=%s mime_type=%s exists=%s size=%s",
        dest_path,
        content_type,
        dest_path.exists(),
        dest_path.stat().st_size,
    )

    return str(dest_path)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def process_audio_answer(upload_file, session_id: int) -> dict:
    """
    Full pipeline: save -> transcribe -> compute metrics.

    Returns dict with audio_file_path, transcript, speech_metrics.
    """
    audio_path = save_upload_audio_file(upload_file, session_id)
    transcript = transcribe_audio(audio_path)
    if not transcript or not transcript.strip():
        raise AudioProcessingError(
            "Khong nhan dien duoc giong noi tu audio. Vui long thu lai.",
            status_code=400,
        )

    speech_metrics = compute_speech_metrics(transcript)

    return {
        "audio_file_path": audio_path,
        "transcript": transcript.strip(),
        "speech_metrics": speech_metrics,
    }
