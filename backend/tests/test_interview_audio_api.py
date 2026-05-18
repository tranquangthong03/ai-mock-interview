"""
Integration tests for the /interviews/{session_id}/answer-audio endpoint.
"""

import io
import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.audio_processing_service import AudioProcessingError, FFMPEG_REQUIRED_MESSAGE


FAKE_AUDIO_RESULT = {
    "audio_file_path": "/uploads/audio/test_audio.webm",
    "transcript": "I built REST APIs with FastAPI, SQLAlchemy, PostgreSQL, authentication, and background jobs.",
    "speech_metrics": {
        "duration_seconds": 25.0,
        "word_count": 12,
        "speech_rate_wpm": 140,
        "filler_words": [],
        "filler_word_count": 0,
        "estimated_pause_count": 1,
        "notes": [],
    },
}

FAKE_AUDIO_RESULT_EMPTY = {
    "audio_file_path": "/uploads/audio/test_audio_empty.webm",
    "transcript": "",
    "speech_metrics": {
        "duration_seconds": 0,
        "word_count": 0,
        "speech_rate_wpm": 0,
        "filler_words": [],
        "filler_word_count": 0,
        "estimated_pause_count": 0,
        "notes": [],
    },
}


class TestSubmitAudioAnswer:
    """Integration tests for POST /interviews/{session_id}/answer-audio."""

    def test_submit_audio_answer_success(self, client, sample_session_with_question):
        """Audio answer should return transcript, speech_metrics, evaluation, next_question."""
        session, question_msg = sample_session_with_question
        session_id = session.id

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session_id}/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["transcript"] == FAKE_AUDIO_RESULT["transcript"]
        assert "speech_metrics" in data
        assert data["speech_metrics"]["word_count"] == 12
        assert "evaluation" in data
        assert "next_question" in data
        assert len(data["next_question"]) > 0

    def test_submit_audio_answer_with_mock_provider_end_to_end(
        self, client, sample_session_with_question, tmp_path, monkeypatch
    ):
        """Route should pass with the real audio service when STT_PROVIDER=mock."""
        monkeypatch.setenv("STT_PROVIDER", "mock")
        monkeypatch.setattr("app.services.audio_processing_service.AUDIO_UPLOAD_DIR", tmp_path)
        session, _ = sample_session_with_question
        fake_audio = io.BytesIO(b"fake audio content")

        response = client.post(
            f"/interviews/{session.id}/answer-audio",
            files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.id
        assert data["transcript"]
        assert "measuring latency" in data["transcript"]
        assert "Em " not in data["transcript"]
        assert data["speech_metrics"]["word_count"] > 0
        assert data["evaluation"] is not None
        assert "short_feedback" in data["evaluation"]
        assert "Câu trả lời" in data["evaluation"]["short_feedback"]
        assert data["next_question"]

    def test_submit_audio_answer_missing_session_returns_404(self, client):
        """Non-existent session should return 404."""
        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                "/interviews/9999/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 404

    def test_submit_audio_answer_completed_session_returns_400(
        self, client, sample_session_with_question, db_session
    ):
        """Completed session should return 400."""
        session, _ = sample_session_with_question
        session.status = "completed"
        db_session.commit()

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session.id}/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 400

    def test_submit_audio_answer_empty_transcript_returns_400(
        self, client, sample_session_with_question
    ):
        """Empty transcript from STT should return 400."""
        session, _ = sample_session_with_question

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            side_effect=ValueError("Không nhận diện được giọng nói từ audio."),
        ):
            response = client.post(
                f"/interviews/{session.id}/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 400
        assert "Không nhận diện" in response.json()["detail"]

    def test_submit_audio_answer_stt_dependency_error_is_clear(
        self, client, sample_session_with_question
    ):
        """Missing ffmpeg should return a clear API error instead of a vague 500."""
        session, _ = sample_session_with_question
        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            side_effect=AudioProcessingError(FFMPEG_REQUIRED_MESSAGE, status_code=503),
        ):
            response = client.post(
                f"/interviews/{session.id}/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 503
        assert "FFmpeg is required" in response.json()["detail"]

    def test_submit_audio_answer_missing_file_field_returns_422(
        self, client, sample_session_with_question
    ):
        """The audio_file form field is required by the endpoint."""
        session, _ = sample_session_with_question

        response = client.post(f"/interviews/{session.id}/answer-audio", files={})

        assert response.status_code == 422

    def test_submit_audio_response_has_all_fields(
        self, client, sample_session_with_question
    ):
        """Response must contain transcript, speech_metrics, evaluation, next_question."""
        session, _ = sample_session_with_question

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session.id}/answer-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        data = response.json()
        assert "transcript" in data
        assert "speech_metrics" in data
        assert "evaluation" in data
        assert "next_question" in data
        assert "status" in data
        assert "session_id" in data
        assert "round_number" in data

        # Verify speech_metrics structure
        sm = data["speech_metrics"]
        assert "duration_seconds" in sm
        assert "word_count" in sm
        assert "speech_rate_wpm" in sm
        assert "filler_words" in sm

    def test_text_answer_endpoint_still_works(self, client, sample_session_with_question):
        """Text answer endpoint must still work after adding audio endpoint."""
        session, _ = sample_session_with_question

        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "Em đã dùng FastAPI để xây dựng REST API."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["candidate_answer"] == "Em đã dùng FastAPI để xây dựng REST API."
        assert "evaluation" in data
        assert "next_question" in data
