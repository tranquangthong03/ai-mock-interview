"""
Tests for the English interview / Vietnamese feedback language policy.
"""

import sys
import types
from unittest.mock import patch

from app.services.answer_evaluation_service import (
    EVALUATION_SYSTEM_PROMPT,
    build_evaluation_prompt,
)
from app.services.audio_processing_service import (
    _transcribe_faster_whisper,
    _transcribe_mock,
    _transcribe_whisper,
)
from app.services.interview_orchestrator_service import (
    FIRST_QUESTION_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    RETRY_SYSTEM_PROMPT,
    generate_first_question,
)
from app.services.report_generation_service import REPORT_SYSTEM_PROMPT


def test_question_prompts_require_english_only():
    for prompt in (FIRST_QUESTION_SYSTEM_PROMPT, FOLLOWUP_SYSTEM_PROMPT, RETRY_SYSTEM_PROMPT):
        lower = prompt.lower()
        assert "english only" in lower
        assert "do not ask vietnamese" in lower or "do not use vietnamese" in lower
        assert "return only" in lower


def test_generate_first_question_returns_llm_question_without_translation(sample_documents):
    cv_doc, jd_doc = sample_documents
    expected_question = "Can you describe how you optimized inference latency in your CNN project?"

    with patch("app.services.interview_orchestrator_service.retrieve_context", return_value=[]), \
         patch("app.services.interview_orchestrator_service.generate_text", return_value=expected_question) as mock_generate:
        result = generate_first_question(cv_doc, jd_doc)

    assert result == expected_question
    _, kwargs = mock_generate.call_args
    assert "English only" in kwargs["system_prompt"]


def test_evaluation_prompt_requires_english_answer_and_vietnamese_feedback():
    prompt = build_evaluation_prompt(
        question="How did you reduce inference latency?",
        answer="I used batching and measured latency after each change.",
        cv_json={"candidate_name": "Test Candidate"},
        jd_json={"job_title": "AI Engineer"},
        rag_context=[],
        interview_history="",
    )

    assert "candidate is expected to answer in English" in prompt
    assert "Return all feedback fields in Vietnamese" in prompt
    assert "trả lời bằng tiếng Anh" in EVALUATION_SYSTEM_PROMPT
    assert "Feedback bằng tiếng Việt" in EVALUATION_SYSTEM_PROMPT


def test_report_prompt_requires_vietnamese_report_and_computed_scores():
    assert "Báo cáo cuối phải viết bằng tiếng Việt" in REPORT_SYSTEM_PROMPT
    assert "giữ nguyên nội dung tiếng Anh gốc" in REPORT_SYSTEM_PROMPT
    assert "Không đưa overall_score và criterion_scores vào JSON" in REPORT_SYSTEM_PROMPT


def test_mock_stt_transcript_is_english():
    transcript = _transcribe_mock("fake.webm")

    assert "I would optimize" in transcript
    assert "measuring latency" in transcript
    assert "Em " not in transcript


def test_openai_whisper_transcribe_uses_english_and_fp16_false(monkeypatch, tmp_path):
    calls = {}

    class FakeModel:
        def transcribe(self, file_path, language, task, fp16, initial_prompt):
            calls["file_path"] = file_path
            calls["language"] = language
            calls["task"] = task
            calls["fp16"] = fp16
            calls["initial_prompt"] = initial_prompt
            return {"text": "English transcript"}

    fake_whisper = types.SimpleNamespace(load_model=lambda model_name: FakeModel())
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)
    monkeypatch.setenv("STT_LANGUAGE", "en")
    audio_path = tmp_path / "answer.webm"
    audio_path.write_bytes(b"fake")

    transcript = _transcribe_whisper(audio_path)

    assert transcript == "English transcript"
    assert calls["language"] == "en"
    assert calls["task"] == "transcribe"
    assert calls["fp16"] is False
    assert "English technical interview answer" in calls["initial_prompt"]


def test_faster_whisper_transcribe_uses_english(monkeypatch, tmp_path):
    calls = {}

    class FakeSegment:
        text = "English transcript"

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            calls["device"] = device
            calls["compute_type"] = compute_type

        def transcribe(self, file_path, language, task, vad_filter, beam_size, initial_prompt):
            calls["file_path"] = file_path
            calls["language"] = language
            calls["task"] = task
            calls["vad_filter"] = vad_filter
            calls["beam_size"] = beam_size
            calls["initial_prompt"] = initial_prompt
            return [FakeSegment()], None

    fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    monkeypatch.setenv("STT_LANGUAGE", "en")
    audio_path = tmp_path / "answer.webm"
    audio_path.write_bytes(b"fake")

    transcript = _transcribe_faster_whisper(audio_path)

    assert transcript == "English transcript"
    assert calls["language"] == "en"
    assert calls["task"] == "transcribe"
    assert calls["vad_filter"] is True
    assert calls["beam_size"] == 5
    assert "English technical interview answer" in calls["initial_prompt"]
    assert calls["device"] == "cpu"
    assert calls["compute_type"] == "int8"
