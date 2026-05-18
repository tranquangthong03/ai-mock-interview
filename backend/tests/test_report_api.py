"""
Tests for report API endpoints.

All tests use:
  - In-memory SQLite test database
  - Mocked LLM service (no real API calls)
  - Mocked RAG service (no real embeddings)
"""

import json
import pytest

from app.models import InterviewReport


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/report — generate report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    """Tests for the report generation endpoint."""

    def test_generate_report_success(
        self, client, db_session, sample_session_with_evaluations
    ):
        """Successfully generate a report for a session with evaluations."""
        session, messages, evaluations = sample_session_with_evaluations

        response = client.post(f"/interviews/{session.id}/report")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session.id
        assert data["overall_score"] > 0
        assert "criterion_scores" in data
        assert "summary" in data
        assert "strengths_summary" in data
        assert isinstance(data["strengths_summary"], list)
        assert "weaknesses_summary" in data
        assert isinstance(data["weaknesses_summary"], list)
        assert "skill_gap_summary" in data
        assert "improvement_plan" in data
        assert "recommended_topics" in data
        assert "final_advice" in data
        assert data["message"] == "Interview report generated successfully"

        # Verify saved to DB
        saved = db_session.query(InterviewReport).filter(
            InterviewReport.session_id == session.id
        ).first()
        assert saved is not None
        assert saved.overall_score > 0

    def test_generate_report_missing_session_returns_404(self, client):
        """Non-existent session returns 404."""
        response = client.post("/interviews/99999/report")
        assert response.status_code == 404

    def test_generate_report_without_evaluations_returns_400(
        self, client, sample_session_with_question
    ):
        """Session without evaluations returns 400."""
        session, _ = sample_session_with_question

        response = client.post(f"/interviews/{session.id}/report")
        assert response.status_code == 400
        assert "evaluation" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/report — get saved report
# ---------------------------------------------------------------------------

class TestGetReport:
    """Tests for retrieving a saved report."""

    def test_get_report_success(
        self, client, db_session, sample_session_with_evaluations
    ):
        """GET report after generating it should return saved data."""
        session, messages, evaluations = sample_session_with_evaluations

        # First generate
        gen_response = client.post(f"/interviews/{session.id}/report")
        assert gen_response.status_code == 200

        # Then retrieve
        response = client.get(f"/interviews/{session.id}/report")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session.id
        assert data["overall_score"] > 0
        assert "criterion_scores" in data
        assert "summary" in data
        assert "created_at" in data
        assert isinstance(data["strengths_summary"], list)

    def test_get_report_missing_returns_404(
        self, client, sample_session_with_evaluations
    ):
        """GET report when none has been generated returns 404."""
        session, messages, evaluations = sample_session_with_evaluations

        response = client.get(f"/interviews/{session.id}/report")
        assert response.status_code == 404
        assert "no report found" in response.json()["detail"].lower()

    def test_get_report_missing_session_returns_404(self, client):
        """GET report for non-existent session returns 404."""
        response = client.get("/interviews/99999/report")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/summary — score summary (no LLM)
# ---------------------------------------------------------------------------

class TestGetSummary:
    """Tests for the summary endpoint."""

    def test_get_summary_success(
        self, client, sample_session_with_evaluations
    ):
        """Summary returns computed score averages."""
        session, messages, evaluations = sample_session_with_evaluations

        response = client.get(f"/interviews/{session.id}/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session.id
        assert data["total_answers"] == 2
        assert data["average_score"] == 7.0  # (7.5 + 6.5) / 2
        assert "criterion_averages" in data
        assert data["criterion_averages"]["relevance"] == 7.5  # (8 + 7) / 2
        assert data["best_criterion"] != ""
        assert data["weakest_criterion"] != ""

    def test_get_summary_does_not_call_llm(
        self, client, db_session, sample_session_with_evaluations
    ):
        """Summary endpoint must NOT call LLM — pure computation."""
        session, messages, evaluations = sample_session_with_evaluations

        # The client fixture already mocks generate_text.
        # If LLM were called, it would return fake data.
        # We verify the summary values are computed from actual DB data,
        # not from any LLM response.
        response = client.get(f"/interviews/{session.id}/summary")
        assert response.status_code == 200

        data = response.json()
        # These values come from the fixture evaluations, not from LLM
        assert data["total_answers"] == 2
        assert data["average_score"] == 7.0
        # (8+7)/2 = 7.5 for relevance
        assert data["criterion_averages"]["relevance"] == 7.5
        # (7+6)/2 = 6.5 for clarity
        assert data["criterion_averages"]["clarity"] == 6.5

    def test_get_summary_missing_session_returns_404(self, client):
        """Summary for non-existent session returns 404."""
        response = client.get("/interviews/99999/summary")
        assert response.status_code == 404
