"""
Tests for interview evaluation API endpoints.

All tests use:
  - In-memory SQLite test database
  - Mocked LLM service (no real API calls)
  - Mocked RAG service (no real embeddings)
"""

import json
# pyrefly: ignore [missing-import]
import pytest

from app.models import AnswerEvaluation, InterviewSession


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/answer — evaluation integration
# ---------------------------------------------------------------------------

class TestSubmitAnswerWithEvaluation:
    """Tests for the updated submit_answer endpoint."""

    def test_submit_answer_creates_evaluation(
        self, client, db_session, sample_session_with_question
    ):
        """Submitting an answer should create an AnswerEvaluation record in DB."""
        session, _ = sample_session_with_question

        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "Em đã xây dựng API đăng nhập bằng FastAPI."},
        )
        assert response.status_code == 200

        # Check DB for evaluation record
        evaluations = (
            db_session.query(AnswerEvaluation)
            .filter(AnswerEvaluation.session_id == session.id)
            .all()
        )
        assert len(evaluations) == 1
        ev = evaluations[0]
        assert ev.score_overall == 7.5
        assert ev.round_number == 1

    def test_submit_answer_response_contains_evaluation_and_next_question(
        self, client, sample_session_with_question
    ):
        """Response must include both evaluation and next_question."""
        session, _ = sample_session_with_question

        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "Em đã làm project về REST API bằng FastAPI và PostgreSQL."},
        )
        assert response.status_code == 200

        data = response.json()

        # Check structure
        assert "evaluation" in data
        assert "next_question" in data
        assert "candidate_answer" in data
        assert data["status"] == "active"

        # Check evaluation content
        ev = data["evaluation"]
        assert ev is not None
        assert ev["score_overall"] == 7.5
        assert "scores" in ev
        assert ev["scores"]["relevance"] == 8
        assert ev["scores"]["clarity"] == 7
        assert len(ev["strengths"]) == 2
        assert len(ev["weaknesses"]) == 2
        assert len(ev["suggestions"]) == 2
        assert ev["improved_answer_suggestion"] != ""
        assert ev["short_feedback"] != ""

        # Check next question exists
        assert data["next_question"] != ""

    def test_submit_empty_answer_returns_400(
        self, client, sample_session_with_question
    ):
        """Empty answer should return 400."""
        session, _ = sample_session_with_question

        # Completely empty
        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": ""},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

        # Whitespace only
        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "   "},
        )
        assert response.status_code == 400

    def test_submit_answer_to_completed_session_returns_400(
        self, client, db_session, sample_session_with_question
    ):
        """Submitting answer to a completed session should return 400."""
        session, _ = sample_session_with_question

        # Mark session as completed
        session.status = "completed"
        db_session.commit()

        response = client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "Some answer"},
        )
        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()

    def test_submit_answer_to_missing_session_returns_404(self, client):
        """Submitting answer to non-existent session should return 404."""
        response = client.post(
            "/interviews/99999/answer",
            json={"answer": "Some answer"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/evaluations
# ---------------------------------------------------------------------------

class TestGetSessionEvaluations:
    """Tests for the evaluations retrieval endpoint."""

    def test_get_session_evaluations_returns_list(
        self, client, sample_session_with_question
    ):
        """After submitting an answer, GET evaluations should return a list."""
        session, _ = sample_session_with_question

        # Submit an answer first to create an evaluation
        client.post(
            f"/interviews/{session.id}/answer",
            json={"answer": "Em đã xây dựng API đăng nhập bằng FastAPI."},
        )

        # Get evaluations
        response = client.get(f"/interviews/{session.id}/evaluations")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session.id
        assert "evaluations" in data
        assert len(data["evaluations"]) == 1

        ev = data["evaluations"][0]
        assert ev["round_number"] == 1
        assert ev["score_overall"] == 7.5
        assert "scores" in ev
        assert ev["question"] != ""
        assert ev["answer"] != ""
        assert "created_at" in ev

    def test_get_evaluations_empty_session(
        self, client, sample_session_with_question
    ):
        """Session with no evaluations should return empty list."""
        session, _ = sample_session_with_question

        response = client.get(f"/interviews/{session.id}/evaluations")
        assert response.status_code == 200

        data = response.json()
        assert data["evaluations"] == []

    def test_get_evaluations_missing_session_returns_404(self, client):
        """Non-existent session should return 404."""
        response = client.get("/interviews/99999/evaluations")
        assert response.status_code == 404
