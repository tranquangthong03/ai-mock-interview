"""
Reports Router

Endpoints:
  POST /interviews/{session_id}/report          – Generate interview report
  GET  /interviews/{session_id}/report          – Get saved report
  GET  /interviews/{session_id}/report/export   – Export report as Markdown or PDF
  GET  /interviews/{session_id}/summary         – Get score summary (no LLM)
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnswerEvaluation, InterviewReport, InterviewSession
from app.schemas import (
    GenerateReportResponse,
    InterviewReportResponse,
    InterviewSummaryResponse,
)
from app.services.report_generation_service import (
    compute_score_summary,
    generate_interview_report,
)
from app.services.report_export_service import (
    get_report_data_for_export,
    build_report_markdown,
    build_report_pdf_bytes,
)

router = APIRouter(prefix="/interviews", tags=["Reports"])


# ---------------------------------------------------------------------------
# POST /interviews/{session_id}/report
# ---------------------------------------------------------------------------

@router.post("/{session_id}/report", response_model=GenerateReportResponse)
def generate_report(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate a comprehensive interview report for a session.

    - Session must exist
    - Session must have at least one evaluation
    - If a report already exists, it will be updated
    """
    # Check session exists
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    # Check evaluations exist
    eval_count = (
        db.query(AnswerEvaluation)
        .filter(AnswerEvaluation.session_id == session_id)
        .count()
    )
    if eval_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Session has no evaluations. Submit and evaluate answers before generating a report.",
        )

    # Generate report
    try:
        report = generate_interview_report(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}",
        )

    return GenerateReportResponse(
        session_id=report["session_id"],
        overall_score=report["overall_score"],
        criterion_scores=report["criterion_scores"],
        summary=report["summary"],
        strengths_summary=report["strengths_summary"],
        weaknesses_summary=report["weaknesses_summary"],
        skill_gap_summary=report["skill_gap_summary"],
        improvement_plan=report["improvement_plan"],
        recommended_topics=report["recommended_topics"],
        final_advice=report["final_advice"],
        message="Interview report generated successfully",
    )


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/report/export
# ---------------------------------------------------------------------------

@router.get("/{session_id}/report/export")
def export_report(
    session_id: int,
    format: str = Query(..., description="Export format: 'markdown' or 'pdf'"),
    db: Session = Depends(get_db),
):
    """
    Export an existing interview report as Markdown or PDF.

    - Does NOT generate a new report — only exports what is already saved.
    - If no report exists, returns 404 with a clear message.
    - Supported formats: ``markdown``, ``pdf``.
    """
    # Validate format
    fmt = format.lower().strip()
    if fmt not in ("markdown", "pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Use 'markdown' or 'pdf'.",
        )

    # Retrieve report data (raises ValueError if not found)
    try:
        report_data = get_report_data_for_export(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    filename_base = f"interview_report_session_{session_id}"

    if fmt == "markdown":
        md_content = build_report_markdown(report_data)
        return Response(
            content=md_content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.md"',
            },
        )

    # fmt == "pdf"
    pdf_bytes = build_report_pdf_bytes(report_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/report
# ---------------------------------------------------------------------------

@router.get("/{session_id}/report", response_model=InterviewReportResponse)
def get_report(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the saved interview report for a session.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    report = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No report found for this session. Generate one first with POST.",
        )

    # Parse JSON fields
    def _parse_json_list(val):
        if not val:
            return []
        try:
            result = json.loads(val)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_json_dict(val):
        if not val:
            return {}
        try:
            result = json.loads(val)
            return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    return InterviewReportResponse(
        session_id=report.session_id,
        overall_score=report.overall_score,
        criterion_scores=_parse_json_dict(report.criterion_scores_json),
        summary=report.summary or "",
        strengths_summary=_parse_json_list(report.strengths_summary),
        weaknesses_summary=_parse_json_list(report.weaknesses_summary),
        skill_gap_summary=_parse_json_list(report.skill_gap_summary),
        improvement_plan=_parse_json_list(report.improvement_plan),
        recommended_topics=_parse_json_list(report.recommended_topics),
        final_advice=report.final_advice or "",
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /interviews/{session_id}/summary
# ---------------------------------------------------------------------------

@router.get("/{session_id}/summary", response_model=InterviewSummaryResponse)
def get_summary(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get score summary statistics for a session.

    This endpoint does NOT call LLM — it only computes averages
    from existing evaluations.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    evaluations = (
        db.query(AnswerEvaluation)
        .filter(AnswerEvaluation.session_id == session_id)
        .order_by(AnswerEvaluation.created_at)
        .all()
    )

    summary = compute_score_summary(evaluations)

    return InterviewSummaryResponse(
        session_id=session_id,
        total_answers=summary["total_answers"],
        average_score=summary["average_score"],
        criterion_averages=summary["criterion_averages"],
        best_criterion=summary["best_criterion"],
        weakest_criterion=summary["weakest_criterion"],
    )
