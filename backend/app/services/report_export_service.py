"""
Report Export Service

Provides functions to export an existing interview report as:
  - Markdown (.md) with Vietnamese-formatted sections
  - PDF (.pdf) via reportlab

No LLM calls — only reads pre-generated report data from the database.
"""

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import InterviewReport


# ---------------------------------------------------------------------------
# Criterion label mapping (consistent with frontend)
# ---------------------------------------------------------------------------

CRITERION_LABELS = {
    "relevance": "Relevance (Đúng trọng tâm)",
    "clarity": "Clarity (Rõ ràng)",
    "specificity": "Specificity (Cụ thể)",
    "technical_accuracy": "Technical Accuracy (Kỹ thuật)",
    "jd_alignment": "JD Alignment (Phù hợp JD)",
    "communication": "Communication (Giao tiếp)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_list(val: Any) -> list:
    """Parse a JSON string into a Python list, returning [] on failure."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        result = json.loads(val)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_json_dict(val: Any) -> dict:
    """Parse a JSON string into a Python dict, returning {} on failure."""
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    try:
        result = json.loads(val)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


# ---------------------------------------------------------------------------
# 1. get_report_data_for_export
# ---------------------------------------------------------------------------

def get_report_data_for_export(db: Session, session_id: int) -> dict:
    """
    Look up the InterviewReport for *session_id* and return its data as a
    plain dict ready for rendering.

    Raises ValueError if no report exists for this session.
    """
    report: InterviewReport | None = (
        db.query(InterviewReport)
        .filter(InterviewReport.session_id == session_id)
        .first()
    )
    if not report:
        raise ValueError(
            "Report not found. Please generate the report first."
        )

    return {
        "session_id": report.session_id,
        "overall_score": report.overall_score,
        "criterion_scores": _parse_json_dict(report.criterion_scores_json),
        "summary": report.summary or "",
        "strengths_summary": _parse_json_list(report.strengths_summary),
        "weaknesses_summary": _parse_json_list(report.weaknesses_summary),
        "skill_gap_summary": _parse_json_list(report.skill_gap_summary),
        "improvement_plan": _parse_json_list(report.improvement_plan),
        "recommended_topics": _parse_json_list(report.recommended_topics),
        "final_advice": report.final_advice or "",
        "created_at": (
            report.created_at.isoformat()
            if isinstance(report.created_at, datetime)
            else str(report.created_at or "")
        ),
    }


# ---------------------------------------------------------------------------
# 2. build_report_markdown
# ---------------------------------------------------------------------------

def build_report_markdown(report_data: dict) -> str:
    """Convert report data dict into a well-formatted Vietnamese Markdown string."""

    lines: list[str] = []

    lines.append("# Báo cáo luyện phỏng vấn AI")
    lines.append("")
    lines.append(f"**Session:** #{report_data.get('session_id', '?')}")
    if report_data.get("created_at"):
        lines.append(f"**Ngày tạo:** {report_data['created_at']}")
    lines.append("")

    # ── Tổng quan ──
    lines.append("## Tổng quan")
    lines.append("")
    summary = report_data.get("summary", "")
    lines.append(summary if summary else "_Không có tổng quan._")
    lines.append("")

    # ── Điểm tổng quan ──
    lines.append("## Điểm tổng quan")
    lines.append("")
    overall = report_data.get("overall_score", 0)
    lines.append(f"**Điểm tổng kết: {overall}/10**")
    lines.append("")

    # ── Điểm theo từng tiêu chí ──
    lines.append("## Điểm theo từng tiêu chí")
    lines.append("")
    criterion_scores: dict = report_data.get("criterion_scores", {})
    if criterion_scores:
        lines.append("| Tiêu chí | Điểm |")
        lines.append("|----------|------|")
        for key, val in criterion_scores.items():
            label = CRITERION_LABELS.get(key, key)
            lines.append(f"| {label} | {val}/10 |")
    else:
        lines.append("_Không có dữ liệu điểm theo tiêu chí._")
    lines.append("")

    # ── Điểm mạnh ──
    lines.append("## Điểm mạnh")
    lines.append("")
    strengths = report_data.get("strengths_summary", [])
    if strengths:
        for s in strengths:
            lines.append(f"- {s}")
    else:
        lines.append("_Không có dữ liệu._")
    lines.append("")

    # ── Điểm cần cải thiện ──
    lines.append("## Điểm cần cải thiện")
    lines.append("")
    weaknesses = report_data.get("weaknesses_summary", [])
    if weaknesses:
        for w in weaknesses:
            lines.append(f"- {w}")
    else:
        lines.append("_Không có dữ liệu._")
    lines.append("")

    # ── Skill gaps ──
    lines.append("## Skill gaps")
    lines.append("")
    gaps = report_data.get("skill_gap_summary", [])
    if gaps:
        for g in gaps:
            lines.append(f"- {g}")
    else:
        lines.append("_Không có dữ liệu._")
    lines.append("")

    # ── Kế hoạch cải thiện ──
    lines.append("## Kế hoạch cải thiện")
    lines.append("")
    plan = report_data.get("improvement_plan", [])
    if plan:
        for i, p in enumerate(plan, 1):
            lines.append(f"{i}. {p}")
    else:
        lines.append("_Không có dữ liệu._")
    lines.append("")

    # ── Chủ đề nên ôn tập ──
    lines.append("## Chủ đề nên ôn tập")
    lines.append("")
    topics = report_data.get("recommended_topics", [])
    if topics:
        lines.append(", ".join(f"`{t}`" for t in topics))
    else:
        lines.append("_Không có dữ liệu._")
    lines.append("")

    # ── Lời khuyên cuối ──
    lines.append("## Lời khuyên cuối")
    lines.append("")
    advice = report_data.get("final_advice", "")
    lines.append(advice if advice else "_Không có lời khuyên._")
    lines.append("")

    # ── Footer ──
    lines.append("---")
    lines.append("_Báo cáo được tạo bởi AI Mock Interviewer._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. build_report_pdf_bytes
# ---------------------------------------------------------------------------

def build_report_pdf_bytes(report_data: dict) -> bytes:
    """
    Generate a PDF document from *report_data* using reportlab.

    The default reportlab fonts (Helvetica family) do **not** include
    Vietnamese glyphs with diacritics.  We attempt to register the
    DejaVu Sans font which ships with many systems and supports
    Vietnamese.  If unavailable we fall back to Helvetica (diacritics
    may render incorrectly in that case).
    """
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Try to register a Unicode-capable font ──
    _font_name = "Helvetica"
    _font_name_bold = "Helvetica-Bold"

    _candidate_fonts = [
        # Windows
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        # Linux / common paths
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]

    for regular_path, bold_path in _candidate_fonts:
        try:
            pdfmetrics.registerFont(TTFont("UniFont", regular_path))
            pdfmetrics.registerFont(TTFont("UniFont-Bold", bold_path))
            _font_name = "UniFont"
            _font_name_bold = "UniFont-Bold"
            break
        except Exception:
            continue

    # ── Styles ──
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=_font_name_bold,
        fontSize=18,
        spaceAfter=6 * mm,
        alignment=TA_CENTER,
    )
    style_h2 = ParagraphStyle(
        "ReportH2",
        parent=styles["Heading2"],
        fontName=_font_name_bold,
        fontSize=13,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    )
    style_body = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName=_font_name,
        fontSize=10,
        leading=14,
        spaceAfter=2 * mm,
    )
    style_meta = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName=_font_name,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    style_bullet = ParagraphStyle(
        "ReportBullet",
        parent=style_body,
        leftIndent=10 * mm,
        bulletIndent=5 * mm,
    )
    style_footer = ParagraphStyle(
        "ReportFooter",
        parent=styles["Normal"],
        fontName=_font_name,
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceBefore=8 * mm,
    )

    # ── Build story ──
    story: list = []

    # Title
    story.append(Paragraph("Báo cáo luyện phỏng vấn AI", style_title))
    meta_parts = [f"Session #{report_data.get('session_id', '?')}"]
    if report_data.get("created_at"):
        meta_parts.append(f"Ngày tạo: {report_data['created_at']}")
    story.append(Paragraph(" · ".join(meta_parts), style_meta))

    # Tổng quan
    story.append(Paragraph("Tổng quan", style_h2))
    story.append(
        Paragraph(
            report_data.get("summary", "") or "Không có tổng quan.",
            style_body,
        )
    )

    # Điểm tổng kết
    story.append(Paragraph("Điểm tổng quan", style_h2))
    overall = report_data.get("overall_score", 0)
    story.append(
        Paragraph(f"Điểm tổng kết: <b>{overall}/10</b>", style_body)
    )

    # Criterion scores table
    criterion_scores: dict = report_data.get("criterion_scores", {})
    if criterion_scores:
        story.append(Paragraph("Điểm theo từng tiêu chí", style_h2))
        table_data = [["Tiêu chí", "Điểm"]]
        for key, val in criterion_scores.items():
            label = CRITERION_LABELS.get(key, key)
            table_data.append([label, f"{val}/10"])

        t = Table(table_data, colWidths=[120 * mm, 30 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), _font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), _font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a2332")),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 3 * mm))

    # Helper to render a bullet list section
    def _add_list_section(title: str, items: list):
        story.append(Paragraph(title, style_h2))
        if items:
            for item in items:
                story.append(
                    Paragraph(f"• {item}", style_bullet)
                )
        else:
            story.append(Paragraph("Không có dữ liệu.", style_body))

    _add_list_section("Điểm mạnh", report_data.get("strengths_summary", []))
    _add_list_section("Điểm cần cải thiện", report_data.get("weaknesses_summary", []))
    _add_list_section("Skill Gaps", report_data.get("skill_gap_summary", []))

    # Improvement plan (numbered)
    story.append(Paragraph("Kế hoạch cải thiện", style_h2))
    plan = report_data.get("improvement_plan", [])
    if plan:
        for i, p in enumerate(plan, 1):
            story.append(Paragraph(f"{i}. {p}", style_bullet))
    else:
        story.append(Paragraph("Không có dữ liệu.", style_body))

    # Recommended topics
    story.append(Paragraph("Chủ đề nên ôn tập", style_h2))
    topics = report_data.get("recommended_topics", [])
    if topics:
        story.append(Paragraph(", ".join(topics), style_body))
    else:
        story.append(Paragraph("Không có dữ liệu.", style_body))

    # Final advice
    story.append(Paragraph("Lời khuyên cuối", style_h2))
    advice = report_data.get("final_advice", "")
    story.append(
        Paragraph(advice if advice else "Không có lời khuyên.", style_body)
    )

    # Footer
    story.append(
        Paragraph("Báo cáo được tạo bởi AI Mock Interviewer.", style_footer)
    )

    # ── Render PDF to bytes ──
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 4. sanitize_filename
# ---------------------------------------------------------------------------

def sanitize_filename(text: str) -> str:
    """
    Create a filesystem-safe filename from *text*.

    Example:
        sanitize_filename("Interview Report Session #1")
        -> "interview_report_session_1"
    """
    # Lowercase, replace spaces/special chars with underscores
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    text = text.strip("_")
    return text or "report"
