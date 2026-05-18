"""
Tests for the report export API endpoint.

Covers:
  - GET /interviews/{session_id}/report/export?format=markdown
  - GET /interviews/{session_id}/report/export?format=pdf
  - Invalid format → 400
  - Missing report → 404
  - Export does NOT call LLM
"""

import json

from unittest.mock import patch

from app.models import InterviewReport


# ---------------------------------------------------------------------------
# Helper: insert a report record directly into the test DB
# ---------------------------------------------------------------------------

def _insert_report(db_session, session_id: int) -> InterviewReport:
    """Insert a pre-built InterviewReport into the test database."""
    report = InterviewReport(
        session_id=session_id,
        overall_score=7.5,
        criterion_scores_json=json.dumps({
            "relevance": 8,
            "clarity": 7,
            "specificity": 7,
            "technical_accuracy": 8,
            "jd_alignment": 8,
            "communication": 7,
        }),
        summary="Ứng viên có nền tảng phù hợp.",
        strengths_summary=json.dumps([
            "Trả lời đúng trọng tâm.",
            "Có liên hệ với project thực tế.",
        ], ensure_ascii=False),
        weaknesses_summary=json.dumps([
            "Thiếu ví dụ cụ thể.",
        ], ensure_ascii=False),
        skill_gap_summary=json.dumps([
            "Cần ôn thêm về testing.",
        ], ensure_ascii=False),
        improvement_plan=json.dumps([
            "Luyện trả lời theo cấu trúc STAR.",
        ], ensure_ascii=False),
        recommended_topics=json.dumps([
            "REST API design",
            "JWT authentication",
        ], ensure_ascii=False),
        final_advice="Nên tập trung câu trả lời cụ thể hơn.",
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExportReportMarkdownSuccess:
    def test_export_report_markdown_success(
        self, client, db_session, sample_session_with_evaluations
    ):
        session, _, _ = sample_session_with_evaluations
        _insert_report(db_session, session.id)

        resp = client.get(
            f"/interviews/{session.id}/report/export",
            params={"format": "markdown"},
        )

        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert f"session_{session.id}.md" in resp.headers.get("content-disposition", "")

        body = resp.text
        assert "# Báo cáo luyện phỏng vấn AI" in body
        assert "## Tổng quan" in body
        assert "7.5/10" in body


class TestExportReportPdfSuccess:
    def test_export_report_pdf_success(
        self, client, db_session, sample_session_with_evaluations
    ):
        session, _, _ = sample_session_with_evaluations
        _insert_report(db_session, session.id)

        resp = client.get(
            f"/interviews/{session.id}/report/export",
            params={"format": "pdf"},
        )

        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert f"session_{session.id}.pdf" in resp.headers.get("content-disposition", "")

        # Valid PDF starts with %PDF-
        assert resp.content[:5] == b"%PDF-"


class TestExportReportInvalidFormat:
    def test_export_report_invalid_format_returns_400(
        self, client, db_session, sample_session_with_evaluations
    ):
        session, _, _ = sample_session_with_evaluations
        _insert_report(db_session, session.id)

        resp = client.get(
            f"/interviews/{session.id}/report/export",
            params={"format": "docx"},
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "Invalid format" in body["detail"]


class TestExportReportMissingReport:
    def test_export_report_missing_report_returns_404(
        self, client, db_session, sample_session_with_evaluations
    ):
        session, _, _ = sample_session_with_evaluations
        # Do NOT insert a report — it should not exist

        resp = client.get(
            f"/interviews/{session.id}/report/export",
            params={"format": "markdown"},
        )

        assert resp.status_code == 404
        body = resp.json()
        assert "generate" in body["detail"].lower() or "not found" in body["detail"].lower()


class TestExportReportDoesNotCallLlm:
    def test_export_report_does_not_call_llm(
        self, client, db_session, sample_session_with_evaluations
    ):
        """Ensure the export endpoint never invokes the LLM generate_text function."""
        session, _, _ = sample_session_with_evaluations
        _insert_report(db_session, session.id)

        with patch(
            "app.services.report_generation_service.generate_text"
        ) as mock_llm:
            resp = client.get(
                f"/interviews/{session.id}/report/export",
                params={"format": "markdown"},
            )
            assert resp.status_code == 200
            mock_llm.assert_not_called()

        with patch(
            "app.services.report_generation_service.generate_text"
        ) as mock_llm:
            resp = client.get(
                f"/interviews/{session.id}/report/export",
                params={"format": "pdf"},
            )
            assert resp.status_code == 200
            mock_llm.assert_not_called()
