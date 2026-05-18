"""
Tests for app.services.report_generation_service

All tests use mocked LLM — no real API calls.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.report_generation_service import (
    build_report_prompt,
    compute_score_summary,
    extract_json_from_llm_response,
    normalize_report_json,
    generate_interview_report,
    CRITERION_KEYS,
)
from tests.conftest import (
    FAKE_REPORT_JSON,
    SAMPLE_CV_JSON,
    SAMPLE_JD_JSON,
)


# ---------------------------------------------------------------------------
# compute_score_summary
# ---------------------------------------------------------------------------

class TestComputeScoreSummary:
    """Tests for score summary computation."""

    def test_compute_score_summary_returns_average_scores(self):
        """Average scores are computed correctly from evaluations."""

        class FakeEval:
            def __init__(self, overall, rel, cla, spe, tech, jd, comm):
                self.score_overall = overall
                self.relevance_score = rel
                self.clarity_score = cla
                self.specificity_score = spe
                self.technical_accuracy_score = tech
                self.jd_alignment_score = jd
                self.communication_score = comm

        evals = [
            FakeEval(8, 9, 7, 8, 9, 8, 7),
            FakeEval(6, 7, 5, 6, 7, 6, 5),
        ]
        result = compute_score_summary(evals)

        assert result["total_answers"] == 2
        assert result["average_score"] == 7.0
        assert result["criterion_averages"]["relevance"] == 8.0
        assert result["criterion_averages"]["clarity"] == 6.0
        assert result["criterion_averages"]["specificity"] == 7.0
        assert result["criterion_averages"]["technical_accuracy"] == 8.0
        assert result["criterion_averages"]["jd_alignment"] == 7.0
        assert result["criterion_averages"]["communication"] == 6.0
        assert result["best_criterion"] in ("relevance", "technical_accuracy")
        assert result["weakest_criterion"] in ("clarity", "communication")

    def test_compute_score_summary_handles_empty_evaluations(self):
        """Empty evaluations return zeroed summary."""
        result = compute_score_summary([])

        assert result["total_answers"] == 0
        assert result["average_score"] == 0.0
        for key in CRITERION_KEYS:
            assert result["criterion_averages"][key] == 0.0
        assert result["best_criterion"] == ""
        assert result["weakest_criterion"] == ""


# ---------------------------------------------------------------------------
# build_report_prompt
# ---------------------------------------------------------------------------

class TestBuildReportPrompt:
    """Tests for prompt construction."""

    def test_build_report_prompt_contains_cv_jd_transcript_evaluations(self):
        """Prompt must include CV, JD, transcript, and evaluation data."""
        cv_json = json.loads(SAMPLE_CV_JSON)
        jd_json = json.loads(SAMPLE_JD_JSON)

        class FakeMessage:
            def __init__(self, role, content, round_number):
                self.role = role
                self.content = content
                self.round_number = round_number

        class FakeEval:
            def __init__(self):
                self.round_number = 1
                self.score_overall = 7.5
                self.relevance_score = 8
                self.clarity_score = 7
                self.specificity_score = 7
                self.technical_accuracy_score = 8
                self.jd_alignment_score = 8
                self.communication_score = 7
                self.strengths = json.dumps(["Tốt"], ensure_ascii=False)
                self.weaknesses = json.dumps(["Cần cải thiện"], ensure_ascii=False)
                self.short_feedback = "Feedback mẫu"

        class FakeSession:
            id = 1

        report_data = {
            "session": FakeSession(),
            "cv_json": cv_json,
            "jd_json": jd_json,
            "messages": [
                FakeMessage("interviewer", "Câu hỏi test?", 1),
                FakeMessage("candidate", "Câu trả lời test.", 1),
            ],
            "evaluations": [FakeEval()],
        }

        score_summary = {
            "total_answers": 1,
            "average_score": 7.5,
            "criterion_averages": {k: 7.5 for k in CRITERION_KEYS},
            "best_criterion": "relevance",
            "weakest_criterion": "communication",
        }

        prompt = build_report_prompt(report_data, score_summary)

        # CV data
        assert "Nguyễn Văn A" in prompt
        # JD data
        assert "Junior Backend Developer" in prompt
        # Transcript
        assert "Câu hỏi test?" in prompt
        assert "Câu trả lời test." in prompt
        # Evaluation
        assert "7.5" in prompt
        # Score summary
        assert "average_score" in prompt


# ---------------------------------------------------------------------------
# extract_json_from_llm_response
# ---------------------------------------------------------------------------

class TestExtractJsonFromLlmResponse:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_json_from_plain_report_response(self):
        """Plain JSON response is parsed correctly."""
        raw = json.dumps(FAKE_REPORT_JSON, ensure_ascii=False)
        result = extract_json_from_llm_response(raw)
        assert result["overall_score"] == 7.5
        assert result["session_id"] == 1
        assert len(result["strengths_summary"]) == 2

    def test_extract_json_from_markdown_report_response(self):
        """JSON wrapped in markdown fences is extracted."""
        inner = json.dumps(FAKE_REPORT_JSON, ensure_ascii=False)
        raw = f"Here is the report:\n```json\n{inner}\n```\nDone."
        result = extract_json_from_llm_response(raw)
        assert result["overall_score"] == 7.5
        assert len(result["recommended_topics"]) == 4

    def test_extract_json_raises_on_invalid(self):
        """Invalid text raises ValueError."""
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            extract_json_from_llm_response("This is not JSON at all")


# ---------------------------------------------------------------------------
# normalize_report_json
# ---------------------------------------------------------------------------

class TestNormalizeReportJson:
    """Tests for report JSON normalization."""

    def test_normalize_report_json_adds_missing_fields(self):
        """Missing fields get sensible defaults."""
        data = {"overall_score": 6}
        score_summary = {
            "average_score": 6,
            "criterion_averages": {k: 5.0 for k in CRITERION_KEYS},
        }
        result = normalize_report_json(data, session_id=1, score_summary=score_summary)

        assert result["session_id"] == 1
        assert result["overall_score"] == 6.0
        assert result["summary"] == ""
        assert result["strengths_summary"] == []
        assert result["weaknesses_summary"] == []
        assert result["skill_gap_summary"] == []
        assert result["improvement_plan"] == []
        assert result["recommended_topics"] == []
        assert result["final_advice"] == ""
        # Should use score_summary as fallback for criterion_scores
        for key in CRITERION_KEYS:
            assert result["criterion_scores"][key] == 5.0

    def test_normalize_report_json_clamps_scores(self):
        """Computed scores from evaluations are used and clamped."""
        data = {
            "overall_score": 15,
            "criterion_scores": {
                "relevance": -3,
                "clarity": 12,
                "specificity": 5,
                "technical_accuracy": 100,
                "jd_alignment": -0.5,
                "communication": 10,
            },
        }
        score_summary = {
            "average_score": 7,
            "criterion_averages": {k: 7.0 for k in CRITERION_KEYS},
        }
        result = normalize_report_json(data, session_id=1, score_summary=score_summary)

        assert result["overall_score"] == 7.0
        for key in CRITERION_KEYS:
            assert result["criterion_scores"][key] == 7.0

    def test_normalize_report_json_handles_null_values(self):
        """Null values are replaced with defaults."""
        data = {
            "overall_score": None,
            "criterion_scores": None,
            "summary": None,
            "strengths_summary": None,
            "weaknesses_summary": None,
            "skill_gap_summary": None,
            "improvement_plan": None,
            "recommended_topics": None,
            "final_advice": None,
        }
        score_summary = {
            "average_score": 5,
            "criterion_averages": {k: 5.0 for k in CRITERION_KEYS},
        }
        result = normalize_report_json(data, session_id=1, score_summary=score_summary)

        assert result["overall_score"] == 5.0  # falls back to average_score
        assert result["summary"] == ""
        assert result["strengths_summary"] == []
        assert result["final_advice"] == ""


# ---------------------------------------------------------------------------
# generate_interview_report (with mock LLM)
# ---------------------------------------------------------------------------

class TestGenerateInterviewReport:
    """Test the full report generation flow with mocked LLM."""

    def test_generate_interview_report_with_mock_llm(
        self, db_session, sample_session_with_evaluations
    ):
        """Full flow: collect data -> compute scores -> LLM -> normalize -> save."""
        session, messages, evaluations = sample_session_with_evaluations

        fake_response = json.dumps(FAKE_REPORT_JSON, ensure_ascii=False)

        with patch(
            "app.services.report_generation_service.generate_text",
            return_value=fake_response,
        ):
            result = generate_interview_report(db_session, session.id)

        assert result["session_id"] == session.id
        assert result["overall_score"] == 7.0
        assert len(result["strengths_summary"]) == 2
        assert len(result["weaknesses_summary"]) == 2
        assert len(result["skill_gap_summary"]) == 2
        assert len(result["improvement_plan"]) == 2
        assert len(result["recommended_topics"]) == 4
        assert result["final_advice"] != ""
        assert result["summary"] != ""

        # Verify it was saved to DB
        from app.models import InterviewReport
        saved = db_session.query(InterviewReport).filter(
            InterviewReport.session_id == session.id
        ).first()
        assert saved is not None
        assert saved.overall_score == 7.0
