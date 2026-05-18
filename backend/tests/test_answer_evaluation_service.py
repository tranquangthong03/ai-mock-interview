"""
Tests for app.services.answer_evaluation_service

All tests use mocked LLM — no real API calls.
"""

import json
import pytest
from unittest.mock import patch

from app.services.answer_evaluation_service import (
    build_evaluation_prompt,
    extract_json_from_llm_response,
    normalize_evaluation_json,
    evaluate_answer,
)
from tests.conftest import FAKE_EVALUATION_JSON, SAMPLE_CV_JSON, SAMPLE_JD_JSON


# ---------------------------------------------------------------------------
# extract_json_from_llm_response
# ---------------------------------------------------------------------------

class TestExtractJsonFromLlmResponse:
    """Tests for JSON extraction from various LLM response formats."""

    def test_extract_json_from_plain_response(self):
        """LLM returns clean JSON without any wrapping."""
        raw = json.dumps(FAKE_EVALUATION_JSON, ensure_ascii=False)
        result = extract_json_from_llm_response(raw)
        assert result["score_overall"] == 7.5
        assert result["scores"]["relevance"] == 8
        assert len(result["strengths"]) == 2

    def test_extract_json_from_markdown_fence_response(self):
        """LLM wraps JSON in ```json ... ``` markdown block."""
        inner = json.dumps(FAKE_EVALUATION_JSON, ensure_ascii=False)
        raw = f"Here is my evaluation:\n```json\n{inner}\n```\nDone."
        result = extract_json_from_llm_response(raw)
        assert result["score_overall"] == 7.5
        assert result["scores"]["clarity"] == 7

    def test_extract_json_from_plain_fence_response(self):
        """LLM wraps JSON in ``` ... ``` without 'json' label."""
        inner = json.dumps(FAKE_EVALUATION_JSON, ensure_ascii=False)
        raw = f"```\n{inner}\n```"
        result = extract_json_from_llm_response(raw)
        assert result["score_overall"] == 7.5

    def test_extract_json_from_text_with_braces(self):
        """LLM returns JSON embedded in explanatory text."""
        inner = json.dumps({"score_overall": 5, "scores": {}}, ensure_ascii=False)
        raw = f"The evaluation is: {inner} — that's my analysis."
        result = extract_json_from_llm_response(raw)
        assert result["score_overall"] == 5

    def test_extract_json_raises_on_invalid(self):
        """Completely invalid text raises ValueError."""
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            extract_json_from_llm_response("This is not JSON at all")


# ---------------------------------------------------------------------------
# normalize_evaluation_json
# ---------------------------------------------------------------------------

class TestNormalizeEvaluationJson:
    """Tests for evaluation JSON normalization."""

    def test_normalize_evaluation_json_adds_missing_fields(self):
        """Missing fields get sensible defaults."""
        data = {"score_overall": 6}  # missing scores, strengths, etc.
        result = normalize_evaluation_json(data)

        assert result["score_overall"] == 6.0
        assert result["scores"]["relevance"] == 0.0
        assert result["scores"]["clarity"] == 0.0
        assert result["scores"]["specificity"] == 0.0
        assert result["scores"]["technical_accuracy"] == 0.0
        assert result["scores"]["jd_alignment"] == 0.0
        assert result["scores"]["communication"] == 0.0
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["suggestions"] == []
        assert result["improved_answer_suggestion"] == ""
        assert result["short_feedback"] == ""

    def test_normalize_evaluation_json_clamps_scores_to_0_10(self):
        """Scores outside 0–10 are clamped."""
        data = {
            "score_overall": 15,
            "scores": {
                "relevance": -3,
                "clarity": 12,
                "specificity": 5,
                "technical_accuracy": 100,
                "jd_alignment": -0.5,
                "communication": 10,
            },
        }
        result = normalize_evaluation_json(data)
        assert result["score_overall"] == 10.0
        assert result["scores"]["relevance"] == 0.0
        assert result["scores"]["clarity"] == 10.0
        assert result["scores"]["specificity"] == 5.0
        assert result["scores"]["technical_accuracy"] == 10.0
        assert result["scores"]["jd_alignment"] == 0.0
        assert result["scores"]["communication"] == 10.0

    def test_normalize_handles_null_values(self):
        """Null values are replaced with defaults."""
        data = {
            "score_overall": None,
            "scores": None,
            "strengths": None,
            "weaknesses": None,
            "suggestions": None,
            "improved_answer_suggestion": None,
            "short_feedback": None,
        }
        result = normalize_evaluation_json(data)
        assert result["score_overall"] == 0.0
        assert result["scores"]["relevance"] == 0.0
        assert result["strengths"] == []
        assert result["improved_answer_suggestion"] == ""

    def test_normalize_preserves_valid_data(self):
        """Valid data passes through unchanged."""
        result = normalize_evaluation_json(FAKE_EVALUATION_JSON)
        assert result["score_overall"] == 7.5
        assert result["scores"]["relevance"] == 8
        assert len(result["strengths"]) == 2
        assert len(result["weaknesses"]) == 2
        assert result["short_feedback"] != ""


# ---------------------------------------------------------------------------
# build_evaluation_prompt
# ---------------------------------------------------------------------------

class TestBuildEvaluationPrompt:
    """Tests for prompt construction."""

    def test_build_evaluation_prompt_contains_question_answer_cv_jd(self):
        """Prompt must include question, answer, CV data, and JD data."""
        cv_json = json.loads(SAMPLE_CV_JSON)
        jd_json = json.loads(SAMPLE_JD_JSON)

        prompt = build_evaluation_prompt(
            question="Bạn hãy mô tả project gần nhất?",
            answer="Em đã làm API đăng nhập bằng FastAPI.",
            cv_json=cv_json,
            jd_json=jd_json,
            rag_context=[{"content": "FastAPI project info"}],
            interview_history="[Vòng 1] Người phỏng vấn: ...",
        )

        assert "Bạn hãy mô tả project gần nhất?" in prompt
        assert "Em đã làm API đăng nhập bằng FastAPI." in prompt
        assert "Nguyễn Văn A" in prompt  # from CV
        assert "Junior Backend Developer" in prompt  # from JD
        assert "FastAPI project info" in prompt  # from RAG context
        assert "Vòng 1" in prompt  # from history

    def test_build_evaluation_prompt_handles_empty_context(self):
        """Prompt works with empty CV/JD and no RAG context."""
        prompt = build_evaluation_prompt(
            question="Test question?",
            answer="Test answer.",
            cv_json={},
            jd_json={},
            rag_context=[],
            interview_history="",
        )
        assert "Test question?" in prompt
        assert "Test answer." in prompt
        assert "Không có context bổ sung" in prompt


# ---------------------------------------------------------------------------
# evaluate_answer (with mock LLM)
# ---------------------------------------------------------------------------

class TestEvaluateAnswer:
    """Tests for the main evaluate_answer function with mocked LLM."""

    def test_evaluate_answer_with_mock_llm_returns_valid_evaluation(self):
        """evaluate_answer returns normalized evaluation dict when LLM is mocked."""
        fake_response = json.dumps(FAKE_EVALUATION_JSON, ensure_ascii=False)

        # Create mock document objects
        class MockDocument:
            def __init__(self, parsed_json):
                self.parsed_json = parsed_json

        cv_doc = MockDocument(SAMPLE_CV_JSON)
        jd_doc = MockDocument(SAMPLE_JD_JSON)

        with patch(
            "app.services.answer_evaluation_service.generate_text",
            return_value=fake_response,
        ):
            result = evaluate_answer(
                question="Bạn hãy mô tả project gần nhất?",
                answer="Em đã xây dựng API đăng nhập bằng FastAPI.",
                cv_document=cv_doc,
                jd_document=jd_doc,
                rag_context=[],
                interview_history="",
            )

        assert result["score_overall"] == 7.5
        assert result["scores"]["relevance"] == 8
        assert len(result["strengths"]) == 2
        assert len(result["weaknesses"]) == 2
        assert len(result["suggestions"]) == 2
        assert result["improved_answer_suggestion"] != ""
        assert result["short_feedback"] != ""
        assert "_raw_response" in result  # audit trail
