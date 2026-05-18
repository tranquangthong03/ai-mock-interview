"""
Report Generation Service

Generates a comprehensive interview report after a session ends.

Functions:
  - get_session_report_data: Collect all data for a session
  - compute_score_summary: Calculate average scores from evaluations
  - build_report_prompt: Construct the LLM prompt
  - extract_json_from_llm_response: Parse JSON from raw LLM text
  - normalize_report_json: Ensure all fields exist with valid values
  - generate_interview_report: Orchestrate the full report flow
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    AnswerEvaluation,
    Document,
    InterviewMessage,
    InterviewReport,
    InterviewSession,
)
from app.services.language_policy import REPORT_LANGUAGE
from app.services.llm_service import generate_text


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def get_session_report_data(db: Session, session_id: int) -> dict:
    """
    Collect all data needed to generate a report for a session.

    Returns a dict with keys:
      session, cv_document, jd_document, messages, evaluations,
      cv_json, jd_json
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise ValueError(f"Interview session {session_id} not found.")

    cv_doc = db.query(Document).filter(Document.id == session.cv_document_id).first()
    jd_doc = db.query(Document).filter(Document.id == session.jd_document_id).first()

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.created_at)
        .all()
    )

    evaluations = (
        db.query(AnswerEvaluation)
        .filter(AnswerEvaluation.session_id == session_id)
        .order_by(AnswerEvaluation.created_at)
        .all()
    )

    # Parse CV/JD JSON
    cv_json = {}
    jd_json = {}
    try:
        if cv_doc and cv_doc.parsed_json:
            cv_json = json.loads(cv_doc.parsed_json)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        if jd_doc and jd_doc.parsed_json:
            jd_json = json.loads(jd_doc.parsed_json)
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "session": session,
        "cv_document": cv_doc,
        "jd_document": jd_doc,
        "messages": messages,
        "evaluations": evaluations,
        "cv_json": cv_json,
        "jd_json": jd_json,
    }


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

CRITERION_KEYS = [
    "relevance", "clarity", "specificity",
    "technical_accuracy", "jd_alignment", "communication",
]

# Mapping from AnswerEvaluation column names to criterion keys
_SCORE_ATTR_MAP = {
    "relevance": "relevance_score",
    "clarity": "clarity_score",
    "specificity": "specificity_score",
    "technical_accuracy": "technical_accuracy_score",
    "jd_alignment": "jd_alignment_score",
    "communication": "communication_score",
}


def compute_score_summary(evaluations: list) -> dict:
    """
    Compute average scores from a list of AnswerEvaluation ORM objects.

    Returns:
        {
            "total_answers": int,
            "average_score": float,
            "criterion_averages": { "relevance": float, ... },
            "best_criterion": str,
            "weakest_criterion": str,
        }
    """
    if not evaluations:
        return {
            "total_answers": 0,
            "average_score": 0.0,
            "criterion_averages": {k: 0.0 for k in CRITERION_KEYS},
            "best_criterion": "",
            "weakest_criterion": "",
        }

    total = len(evaluations)

    # Average overall
    avg_overall = sum(e.score_overall for e in evaluations) / total

    # Average per criterion
    criterion_averages = {}
    for key in CRITERION_KEYS:
        attr = _SCORE_ATTR_MAP[key]
        values = [getattr(e, attr, 0) or 0 for e in evaluations]
        criterion_averages[key] = round(sum(values) / total, 2)

    # Best and weakest
    best = max(criterion_averages, key=criterion_averages.get)
    weakest = min(criterion_averages, key=criterion_averages.get)

    return {
        "total_answers": total,
        "average_score": round(avg_overall, 2),
        "criterion_averages": criterion_averages,
        "best_criterion": best,
        "weakest_criterion": weakest,
    }


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

REPORT_SYSTEM_PROMPT = """Bạn là AI Interview Coach hỗ trợ sinh viên/fresher cải thiện kỹ năng phỏng vấn.
Hãy tạo báo cáo tổng kết cuối buổi phỏng vấn dựa trên CV, JD, transcript và các đánh giá từng câu trả lời.

Yêu cầu:
- Chỉ trả về JSON hợp lệ
- Không dùng markdown
- Không bọc trong ```json
- Không giải thích ngoài JSON
- Viết bằng tiếng Việt
- Không kết luận ứng viên đậu/rớt
- Không đưa nhận định tuyệt đối về năng lực con người
- Tập trung vào góp ý cải thiện kỹ năng trả lời phỏng vấn
- Nêu điểm mạnh, điểm yếu, skill gaps và kế hoạch luyện tập tiếp theo
- Gợi ý cụ thể, thực tế, phù hợp sinh viên/fresher

Quan trọng về grounding (bám vào dữ liệu thực tế):
- Mọi nhận xét PHẢI dựa trên câu trả lời và evaluations đã lưu.
- Không tự bịa điểm mạnh/yếu nếu không có evidence từ transcript.
- Nếu không đủ dữ liệu, ghi "Chưa đủ dữ liệu để kết luận".
- Mỗi bullet trong strengths/weaknesses/skill_gaps/improvement_plan NÊN có dạng:
  "Nhận xét ... (dựa trên vòng X)"
- Không đưa overall_score và criterion_scores vào JSON — hệ thống sẽ tự tính từ evaluations.
- Báo cáo cuối phải viết bằng tiếng Việt.
- Các field summary, strengths_summary, weaknesses_summary, skill_gap_summary, improvement_plan, recommended_topics và final_advice phải bằng tiếng Việt.
- Nếu trích dẫn câu hỏi phỏng vấn hoặc câu trả lời ứng viên, giữ nguyên nội dung tiếng Anh gốc.
- Không dịch toàn bộ transcript tiếng Anh; chỉ phân tích và góp ý bằng tiếng Việt.

JSON schema bắt buộc:
{
  "session_id": 1,
  "summary": "",
  "strengths_summary": [],
  "weaknesses_summary": [],
  "skill_gap_summary": [],
  "improvement_plan": [],
  "recommended_topics": [],
  "final_advice": ""
}"""


def _format_transcript(messages: list) -> str:
    """Format interview messages into a readable transcript."""
    if not messages:
        return "(Không có transcript)"

    lines = []
    for msg in messages:
        role_label = {
            "interviewer": "Người phỏng vấn",
            "candidate": "Ứng viên",
            "system": "Hệ thống",
        }.get(msg.role, msg.role)
        lines.append(f"[Vòng {msg.round_number}] {role_label}: {msg.content}")
    return "\n".join(lines)


def _format_evaluations(evaluations: list) -> str:
    """Format evaluations into a readable summary for the prompt."""
    if not evaluations:
        return "(Không có đánh giá)"

    lines = []
    for ev in evaluations:
        # Parse list fields
        try:
            strengths = json.loads(ev.strengths) if ev.strengths else []
        except (json.JSONDecodeError, TypeError):
            strengths = []
        try:
            weaknesses = json.loads(ev.weaknesses) if ev.weaknesses else []
        except (json.JSONDecodeError, TypeError):
            weaknesses = []

        lines.append(
            f"Vòng {ev.round_number}: overall={ev.score_overall}, "
            f"relevance={ev.relevance_score}, clarity={ev.clarity_score}, "
            f"specificity={ev.specificity_score}, "
            f"technical_accuracy={ev.technical_accuracy_score}, "
            f"jd_alignment={ev.jd_alignment_score}, "
            f"communication={ev.communication_score}\n"
            f"  Điểm mạnh: {', '.join(strengths) if strengths else 'N/A'}\n"
            f"  Điểm yếu: {', '.join(weaknesses) if weaknesses else 'N/A'}\n"
            f"  Feedback: {ev.short_feedback or 'N/A'}"
        )
    return "\n---\n".join(lines)


def build_report_prompt(report_data: dict, score_summary: dict) -> str:
    """
    Build the user-prompt for the LLM to generate an interview report.

    Args:
        report_data: dict from get_session_report_data()
        score_summary: dict from compute_score_summary()

    Returns:
        Prompt string.
    """
    cv_json = report_data.get("cv_json", {})
    jd_json = report_data.get("jd_json", {})
    messages = report_data.get("messages", [])
    evaluations = report_data.get("evaluations", [])
    session = report_data.get("session")

    cv_str = json.dumps(cv_json, ensure_ascii=False, indent=2)[:3000] if cv_json else "(Không có)"
    jd_str = json.dumps(jd_json, ensure_ascii=False, indent=2)[:3000] if jd_json else "(Không có)"
    transcript_str = _format_transcript(messages)
    evaluations_str = _format_evaluations(evaluations)
    score_str = json.dumps(score_summary, ensure_ascii=False, indent=2)

    session_id = session.id if session else 0

    return f"""Dữ liệu buổi phỏng vấn:

Session ID: {session_id}

CV parsed JSON:
{cv_str}

JD parsed JSON:
{jd_str}

Interview transcript:
{transcript_str}

Evaluation results:
{evaluations_str}

Computed score summary:
{score_str}

Report language: {REPORT_LANGUAGE} (Vietnamese).
Keep original English interview questions and candidate answers if quoting them.
Do not include overall_score or criterion_scores in the JSON; the system uses computed evaluation scores.

Hãy tạo báo cáo tổng kết cuối buổi phỏng vấn theo JSON schema bắt buộc."""


# ---------------------------------------------------------------------------
# JSON extraction & normalization
# ---------------------------------------------------------------------------

def extract_json_from_llm_response(response_text: str) -> dict:
    """
    Extract a JSON dict from raw LLM response text.

    Handles:
      1. Plain JSON string
      2. JSON wrapped in ```json ... ``` or ``` ... ```
      3. First { ... } block in free text

    Raises ValueError if no valid JSON is found.
    """
    text = response_text.strip()

    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: markdown code block
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Attempt 3: first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract valid JSON from LLM response. "
        f"Raw response:\n{text[:500]}"
    )


def _clamp(value, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Clamp a numeric value between min_val and max_val."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(min_val, min(max_val, v))


def normalize_report_json(data: dict, session_id: int, score_summary: dict) -> dict:
    """
    Ensure the report dict has all required fields with valid values.

    Scores are ALWAYS taken from the computed score_summary (based on
    actual AnswerEvaluation records), not from whatever the LLM returned.
    This guarantees the report is grounded in real evaluation data.
    """
    criterion_averages = score_summary.get("criterion_averages", {})

    # Always use computed scores from evaluations — ignore LLM scores
    criterion_scores = {}
    for key in CRITERION_KEYS:
        criterion_scores[key] = _clamp(criterion_averages.get(key, 0))

    overall_score = _clamp(score_summary.get("average_score", 0))

    normalized = {
        "session_id": session_id,
        "overall_score": overall_score,
        "criterion_scores": criterion_scores,
        "summary": data.get("summary") or "",
        "strengths_summary": data.get("strengths_summary") or [],
        "weaknesses_summary": data.get("weaknesses_summary") or [],
        "skill_gap_summary": data.get("skill_gap_summary") or [],
        "improvement_plan": data.get("improvement_plan") or [],
        "recommended_topics": data.get("recommended_topics") or [],
        "final_advice": data.get("final_advice") or "",
    }

    # Ensure list fields contain strings
    for key in ("strengths_summary", "weaknesses_summary", "skill_gap_summary",
                "improvement_plan", "recommended_topics"):
        if not isinstance(normalized[key], list):
            normalized[key] = []
        normalized[key] = [str(item) for item in normalized[key]]

    return normalized


# ---------------------------------------------------------------------------
# Main report generation
# ---------------------------------------------------------------------------

def generate_interview_report(db: Session, session_id: int) -> dict:
    """
    Generate a comprehensive interview report for a session.

    Flow:
      1. Validate session exists and has evaluations
      2. Collect session data
      3. Compute score summary
      4. Build LLM prompt
      5. Call LLM
      6. Parse and normalize response
      7. Save or update InterviewReport in DB
      8. Return normalized report dict

    Args:
        db: SQLAlchemy session.
        session_id: ID of the interview session.

    Returns:
        Normalized report dict.
    """
    # 1. Collect data
    report_data = get_session_report_data(db, session_id)

    session = report_data["session"]
    evaluations = report_data["evaluations"]

    if not evaluations:
        raise ValueError(
            f"Session {session_id} has no evaluations. "
            "Cannot generate report without evaluations."
        )

    # 2. Compute score summary
    score_summary = compute_score_summary(evaluations)

    # 3. Build prompt
    prompt = build_report_prompt(report_data, score_summary)

    # 4. Call LLM
    print(f"[Report] Generating interview report for session {session_id}...")
    raw_response = generate_text(
        prompt=prompt,
        system_prompt=REPORT_SYSTEM_PROMPT,
    )

    # 5. Parse and normalize
    report_json = extract_json_from_llm_response(raw_response)
    normalized = normalize_report_json(report_json, session_id, score_summary)

    # 6. Save or update in DB
    existing_report = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).first()

    if existing_report:
        # Update existing report
        existing_report.overall_score = normalized["overall_score"]
        existing_report.criterion_scores_json = json.dumps(
            normalized["criterion_scores"], ensure_ascii=False
        )
        existing_report.summary = normalized["summary"]
        existing_report.strengths_summary = json.dumps(
            normalized["strengths_summary"], ensure_ascii=False
        )
        existing_report.weaknesses_summary = json.dumps(
            normalized["weaknesses_summary"], ensure_ascii=False
        )
        existing_report.skill_gap_summary = json.dumps(
            normalized["skill_gap_summary"], ensure_ascii=False
        )
        existing_report.improvement_plan = json.dumps(
            normalized["improvement_plan"], ensure_ascii=False
        )
        existing_report.recommended_topics = json.dumps(
            normalized["recommended_topics"], ensure_ascii=False
        )
        existing_report.final_advice = normalized["final_advice"]
        existing_report.raw_report_json = json.dumps(normalized, ensure_ascii=False)
        existing_report.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_report)
    else:
        # Create new report
        new_report = InterviewReport(
            session_id=session_id,
            overall_score=normalized["overall_score"],
            criterion_scores_json=json.dumps(
                normalized["criterion_scores"], ensure_ascii=False
            ),
            summary=normalized["summary"],
            strengths_summary=json.dumps(
                normalized["strengths_summary"], ensure_ascii=False
            ),
            weaknesses_summary=json.dumps(
                normalized["weaknesses_summary"], ensure_ascii=False
            ),
            skill_gap_summary=json.dumps(
                normalized["skill_gap_summary"], ensure_ascii=False
            ),
            improvement_plan=json.dumps(
                normalized["improvement_plan"], ensure_ascii=False
            ),
            recommended_topics=json.dumps(
                normalized["recommended_topics"], ensure_ascii=False
            ),
            final_advice=normalized["final_advice"],
            raw_report_json=json.dumps(normalized, ensure_ascii=False),
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

    return normalized
