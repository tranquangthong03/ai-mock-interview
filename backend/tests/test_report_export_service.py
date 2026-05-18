"""
Tests for report_export_service.py

Covers:
  - Markdown generation (required sections, scores, empty lists)
  - PDF generation (returns valid bytes)
  - Filename sanitizer
"""

import pytest

from app.services.report_export_service import (
    build_report_markdown,
    build_report_pdf_bytes,
    sanitize_filename,
)


# ---------------------------------------------------------------------------
# Sample report data used across tests
# ---------------------------------------------------------------------------

SAMPLE_REPORT_DATA = {
    "session_id": 1,
    "overall_score": 7.5,
    "criterion_scores": {
        "relevance": 8,
        "clarity": 7,
        "specificity": 7,
        "technical_accuracy": 8,
        "jd_alignment": 8,
        "communication": 7,
    },
    "summary": "Ứng viên có nền tảng phù hợp với vị trí đang ứng tuyển.",
    "strengths_summary": [
        "Trả lời đúng trọng tâm nhiều câu hỏi.",
        "Có liên hệ với project thực tế.",
    ],
    "weaknesses_summary": [
        "Một số câu trả lời còn thiếu ví dụ cụ thể.",
    ],
    "skill_gap_summary": [
        "Cần ôn thêm về testing.",
        "Cần trình bày rõ hơn về database design.",
    ],
    "improvement_plan": [
        "Luyện trả lời theo cấu trúc STAR.",
        "Chuẩn bị 2 câu chuyện project rõ ràng.",
    ],
    "recommended_topics": [
        "REST API design",
        "JWT authentication",
        "Unit testing",
    ],
    "final_advice": "Ứng viên nên tập trung làm câu trả lời cụ thể hơn.",
    "created_at": "2026-05-13T10:00:00",
}


EMPTY_REPORT_DATA = {
    "session_id": 99,
    "overall_score": 0,
    "criterion_scores": {},
    "summary": "",
    "strengths_summary": [],
    "weaknesses_summary": [],
    "skill_gap_summary": [],
    "improvement_plan": [],
    "recommended_topics": [],
    "final_advice": "",
    "created_at": "",
}


# ---------------------------------------------------------------------------
# Markdown tests
# ---------------------------------------------------------------------------

class TestBuildReportMarkdown:
    def test_build_report_markdown_contains_required_sections(self):
        md = build_report_markdown(SAMPLE_REPORT_DATA)

        required_sections = [
            "# Báo cáo luyện phỏng vấn AI",
            "## Tổng quan",
            "## Điểm tổng quan",
            "## Điểm theo từng tiêu chí",
            "## Điểm mạnh",
            "## Điểm cần cải thiện",
            "## Skill gaps",
            "## Kế hoạch cải thiện",
            "## Chủ đề nên ôn tập",
            "## Lời khuyên cuối",
        ]

        for section in required_sections:
            assert section in md, f"Missing section: {section}"

    def test_build_report_markdown_contains_scores(self):
        md = build_report_markdown(SAMPLE_REPORT_DATA)

        # Overall score
        assert "7.5/10" in md

        # Criterion scores in table
        assert "8/10" in md
        assert "7/10" in md

        # Criterion labels
        assert "Relevance" in md
        assert "Clarity" in md

    def test_build_report_markdown_contains_content(self):
        md = build_report_markdown(SAMPLE_REPORT_DATA)

        # Summary
        assert "Ứng viên có nền tảng" in md

        # Strengths
        assert "Trả lời đúng trọng tâm" in md

        # Weaknesses
        assert "thiếu ví dụ cụ thể" in md

        # Topics
        assert "REST API design" in md
        assert "JWT authentication" in md

        # Final advice
        assert "câu trả lời cụ thể hơn" in md

    def test_build_report_markdown_handles_empty_lists(self):
        md = build_report_markdown(EMPTY_REPORT_DATA)

        # Should contain placeholder text for empty data
        assert "Không có dữ liệu" in md or "Không có tổng quan" in md

        # Should still have section headers
        assert "## Điểm mạnh" in md
        assert "## Kế hoạch cải thiện" in md

    def test_build_report_markdown_is_string(self):
        md = build_report_markdown(SAMPLE_REPORT_DATA)
        assert isinstance(md, str)
        assert len(md) > 100  # should have substantial content


# ---------------------------------------------------------------------------
# PDF tests
# ---------------------------------------------------------------------------

class TestBuildReportPdfBytes:
    def test_build_report_pdf_bytes_returns_bytes(self):
        pdf = build_report_pdf_bytes(SAMPLE_REPORT_DATA)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    def test_build_report_pdf_bytes_has_pdf_header(self):
        pdf = build_report_pdf_bytes(SAMPLE_REPORT_DATA)
        # All valid PDFs start with %PDF
        assert pdf[:5] == b"%PDF-"

    def test_build_report_pdf_bytes_handles_empty_data(self):
        pdf = build_report_pdf_bytes(EMPTY_REPORT_DATA)
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Filename sanitizer tests
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_sanitize_filename_basic(self):
        result = sanitize_filename("Interview Report Session #1")
        assert result == "interview_report_session_1"

    def test_sanitize_filename_special_chars(self):
        result = sanitize_filename("Report @#$% Test!")
        assert "report" in result
        assert "test" in result
        # No special chars
        assert "@" not in result
        assert "#" not in result

    def test_sanitize_filename_spaces(self):
        result = sanitize_filename("hello   world")
        assert result == "hello_world"

    def test_sanitize_filename_empty(self):
        result = sanitize_filename("")
        assert result == "report"

    def test_sanitize_filename_only_special_chars(self):
        result = sanitize_filename("@#$%^&*()")
        assert result == "report"
