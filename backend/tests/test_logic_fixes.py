"""
Tests for the logic fixes:
  - Transcribe-audio endpoint (transcribe only, no submit)
  - Low-relevance retry question
  - Report uses computed scores from evaluations
  - Report prompt requires evidence
  - Text answer still works
  - Audio answer flow still works
"""

import io
import json
import pytest
from unittest.mock import patch, MagicMock

from app.models import InterviewReport
from app.services.report_generation_service import (
    normalize_report_json,
    compute_score_summary,
    REPORT_SYSTEM_PROMPT,
)
from app.services.interview_orchestrator_service import generate_retry_question

# Reuse fixtures from conftest
from tests.conftest import FAKE_EVALUATION_JSON


# ---------------------------------------------------------------------------
# Fake audio result for transcribe tests
# ---------------------------------------------------------------------------

FAKE_AUDIO_RESULT = {
    "audio_file_path": "/uploads/audio/test_audio.webm",
    "transcript": "Em đã xây dựng REST API bằng FastAPI.",
    "speech_metrics": {
        "duration_seconds": 10.0,
        "word_count": 8,
        "speech_rate_wpm": 140,
        "filler_words": [],
        "filler_word_count": 0,
        "estimated_pause_count": 0,
        "notes": [],
    },
}

# Low-relevance evaluation result
LOW_RELEVANCE_EVALUATION = {
    **FAKE_EVALUATION_JSON,
    "scores": {
        **FAKE_EVALUATION_JSON["scores"],
        "relevance": 2,  # Below the threshold of 4
    },
}


# ---------------------------------------------------------------------------
# 1. Transcribe-audio endpoint tests
# ---------------------------------------------------------------------------

class TestTranscribeAudioEndpoint:
    def test_transcribe_audio_returns_transcript_only(
        self, client, sample_session_with_question
    ):
        """Transcribe endpoint should return transcript + metrics without evaluation."""
        session, _ = sample_session_with_question

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session.id}/transcribe-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.id
        assert data["transcript"] == FAKE_AUDIO_RESULT["transcript"]
        assert "speech_metrics" in data
        assert "audio_file_path" in data

        # Must NOT contain evaluation or next_question
        assert "evaluation" not in data
        assert "next_question" not in data

    def test_transcribe_audio_does_not_submit_answer(
        self, client, sample_session_with_question, db_session
    ):
        """Transcribe endpoint must not save a candidate message."""
        session, _ = sample_session_with_question

        from app.models import InterviewMessage

        msg_count_before = (
            db_session.query(InterviewMessage)
            .filter(
                InterviewMessage.session_id == session.id,
                InterviewMessage.role == "candidate",
            )
            .count()
        )

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session.id}/transcribe-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 200

        msg_count_after = (
            db_session.query(InterviewMessage)
            .filter(
                InterviewMessage.session_id == session.id,
                InterviewMessage.role == "candidate",
            )
            .count()
        )

        assert msg_count_after == msg_count_before, "No candidate message should be saved"

    def test_transcribe_audio_completed_session_returns_400(
        self, client, sample_session_with_question, db_session
    ):
        """Completed session should reject transcription."""
        session, _ = sample_session_with_question
        session.status = "completed"
        db_session.commit()

        fake_audio = io.BytesIO(b"fake audio content")

        with patch(
            "app.routers.interviews.process_audio_answer",
            return_value=FAKE_AUDIO_RESULT,
        ):
            response = client.post(
                f"/interviews/{session.id}/transcribe-audio",
                files={"audio_file": ("answer.webm", fake_audio, "audio/webm")},
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# 2. Low-relevance retry question tests
# ---------------------------------------------------------------------------

class TestLowRelevanceRetry:
    def test_low_relevance_answer_generates_retry_question(
        self, client, sample_session_with_question
    ):
        """When relevance < 4, the system should generate a retry question."""
        session, _ = sample_session_with_question

        # Mock evaluation with low relevance
        def fake_generate_low_relevance(prompt: str, system_prompt: str = "") -> str:
            if "đánh giá" in system_prompt.lower() or "rubric" in prompt.lower():
                return json.dumps(LOW_RELEVANCE_EVALUATION, ensure_ascii=False)
            elif "hỏi lại" in system_prompt.lower() or "trọng tâm" in system_prompt.lower():
                return "Bạn có thể quay lại câu hỏi về FastAPI không? Tôi muốn nghe về project cụ thể của bạn."
            else:
                return "Câu hỏi follow-up bình thường"

        with patch("app.services.answer_evaluation_service.generate_text", side_effect=fake_generate_low_relevance), \
             patch("app.services.interview_orchestrator_service.generate_text", side_effect=fake_generate_low_relevance), \
             patch("app.services.rag_service.get_embedding_model"), \
             patch("app.services.rag_service.get_collection"), \
             patch("app.routers.interviews.retrieve_context", return_value=[]), \
             patch("app.services.interview_orchestrator_service.retrieve_context", return_value=[]):
            response = client.post(
                f"/interviews/{session.id}/answer",
                json={"answer": "Tôi thích ăn phở."},
            )

        assert response.status_code == 200
        data = response.json()
        # The evaluation should have low relevance
        assert data["evaluation"]["scores"]["relevance"] == 2
        # There should still be a next_question
        assert len(data["next_question"]) > 0


# ---------------------------------------------------------------------------
# 3. Report uses computed scores tests
# ---------------------------------------------------------------------------

class TestReportUsesComputedScores:
    def test_report_uses_computed_scores_from_evaluations(self):
        """normalize_report_json should always use computed scores, not LLM scores."""
        llm_data = {
            "overall_score": 9.5,  # LLM says 9.5
            "criterion_scores": {
                "relevance": 9,
                "clarity": 10,
                "specificity": 9,
                "technical_accuracy": 10,
                "jd_alignment": 9,
                "communication": 10,
            },
            "summary": "Test summary",
            "strengths_summary": ["Good"],
            "weaknesses_summary": ["Bad"],
            "skill_gap_summary": [],
            "improvement_plan": [],
            "recommended_topics": [],
            "final_advice": "Keep going",
        }

        computed_summary = {
            "average_score": 7.0,  # Actual computed: 7.0
            "criterion_averages": {
                "relevance": 7.5,
                "clarity": 6.5,
                "specificity": 7.0,
                "technical_accuracy": 7.0,
                "jd_alignment": 7.5,
                "communication": 6.5,
            },
        }

        result = normalize_report_json(llm_data, session_id=1, score_summary=computed_summary)

        # Scores must come from computed_summary, NOT from LLM
        assert result["overall_score"] == 7.0
        assert result["criterion_scores"]["relevance"] == 7.5
        assert result["criterion_scores"]["clarity"] == 6.5
        assert result["criterion_scores"]["communication"] == 6.5

        # Text fields should still come from LLM
        assert result["summary"] == "Test summary"
        assert result["strengths_summary"] == ["Good"]

    def test_report_prompt_requires_evidence(self):
        """The report system prompt must mention grounding requirements."""
        prompt_lower = REPORT_SYSTEM_PROMPT.lower()
        assert "evidence" in prompt_lower or "dựa trên" in prompt_lower
        assert "không tự bịa" in prompt_lower or "không bịa" in prompt_lower
        assert "dựa trên vòng" in prompt_lower


# ---------------------------------------------------------------------------
# 4. Existing flows still work tests
# ---------------------------------------------------------------------------

class TestExistingFlowsStillWork:
    def test_text_answer_still_works(self, client, sample_session_with_question):
        """Text answer endpoint must still work after all changes."""
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
        assert len(data["next_question"]) > 0

    def test_audio_answer_flow_still_works(self, client, sample_session_with_question):
        """Audio answer endpoint must still work after adding transcribe endpoint."""
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

        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] == FAKE_AUDIO_RESULT["transcript"]
        assert "evaluation" in data
        assert "next_question" in data
