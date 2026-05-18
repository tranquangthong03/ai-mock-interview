"""
Answer Evaluation Service

Evaluates candidate answers using LLM-based rubric scoring.

Functions:
  - build_evaluation_prompt: Construct the full prompt for the LLM
  - extract_json_from_llm_response: Parse JSON from raw LLM text
  - normalize_evaluation_json: Ensure all fields exist, clamp scores 0-10
  - evaluate_answer: Orchestrate the full evaluation flow
"""

import json
import re

from app.services.language_policy import CANDIDATE_EXPECTED_LANGUAGE, FEEDBACK_LANGUAGE
from app.services.llm_service import generate_text


# ---------------------------------------------------------------------------
# Evaluation prompt
# ---------------------------------------------------------------------------

EVALUATION_SYSTEM_PROMPT = f"""Bạn là chuyên gia phỏng vấn kỹ thuật và career coach cho sinh viên/fresher.
Hãy đánh giá câu trả lời của ứng viên dựa trên câu hỏi, câu trả lời, CV, JD và context liên quan.

Language policy:
- Interviewer questions are in English.
- The candidate is expected to answer in {CANDIDATE_EXPECTED_LANGUAGE}.
- Treat the answer as an English interview answer.
- All human-readable feedback, comments, suggestions, strengths, weaknesses, explanations, improved answer suggestions, and short_feedback must be in {FEEDBACK_LANGUAGE} (Vietnamese).
- Keep criterion keys in English exactly as required by the JSON schema.
- If the candidate answers in Vietnamese, mostly Vietnamese, or heavily mixed Vietnamese-English, still evaluate it, but mention in Vietnamese that the candidate should answer in English and reduce the communication score appropriately.
- Khi cần nhắc về ngôn ngữ, hãy dùng nội dung tiếng Việt rõ ràng rằng ứng viên nên trả lời bằng tiếng Anh.
- Do not translate the whole candidate answer unless a short explanation requires it.

Tiêu chí đánh giá:
1. relevance: câu trả lời có đúng trọng tâm câu hỏi không
2. clarity: câu trả lời có rõ ràng, mạch lạc không
3. specificity: có ví dụ cụ thể, chi tiết thực tế không
4. technical_accuracy: kiến thức kỹ thuật có đúng không
5. jd_alignment: câu trả lời có liên quan yêu cầu trong JD không
6. communication: cách diễn đạt có dễ hiểu, phù hợp phỏng vấn không, và có dùng đúng ngôn ngữ tiếng Anh được kỳ vọng không

Yêu cầu output:
- Chỉ trả về JSON hợp lệ
- Không dùng markdown
- Không bọc trong ```json
- Không giải thích ngoài JSON
- Điểm từ 0 đến 10
- Feedback bằng tiếng Việt
- Không kết luận đậu/rớt
- Không đưa ra nhận định tuyệt đối về năng lực con người
- Chỉ đóng vai trò hỗ trợ luyện tập phỏng vấn

JSON schema bắt buộc:
{{
  "score_overall": 0,
  "scores": {{
    "relevance": 0,
    "clarity": 0,
    "specificity": 0,
    "technical_accuracy": 0,
    "jd_alignment": 0,
    "communication": 0
  }},
  "strengths": [],
  "weaknesses": [],
  "suggestions": [],
  "improved_answer_suggestion": "",
  "short_feedback": ""
}}"""


def build_evaluation_prompt(
    question: str,
    answer: str,
    cv_json: dict,
    jd_json: dict,
    rag_context: list[dict],
    interview_history: str,
) -> str:
    """
    Build the user-prompt sent to the LLM for answer evaluation.
    """
    cv_str = json.dumps(cv_json, ensure_ascii=False, indent=2)[:3000] if cv_json else "(Không có)"
    jd_str = json.dumps(jd_json, ensure_ascii=False, indent=2)[:3000] if jd_json else "(Không có)"

    if rag_context:
        rag_text = "\n---\n".join(
            r.get("content", "") for r in rag_context
        )
    else:
        rag_text = "(Không có context bổ sung)"

    return f"""Dữ liệu đánh giá:

Question:
{question}

Answer:
{answer}

CV parsed JSON:
{cv_str}

JD parsed JSON:
{jd_str}

RAG context (các đoạn liên quan từ CV/JD):
{rag_text}

Interview history:
{interview_history}

Language requirements:
- The interviewer question is in English.
- The candidate is expected to answer in English.
- Return all feedback fields in Vietnamese.
- If the answer is Vietnamese or heavily mixed Vietnamese-English, mention in Vietnamese that the candidate should answer in English.

Hãy đánh giá câu trả lời theo rubric và trả về JSON theo schema bắt buộc."""


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def extract_json_from_llm_response(response_text: str) -> dict:
    """
    Extract a JSON dict from raw LLM response text.
    """
    text = response_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

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


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _clamp(value, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Clamp a numeric value between min_val and max_val."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(min_val, min(max_val, v))


def normalize_evaluation_json(data: dict) -> dict:
    """
    Ensure the evaluation dict has all required fields with valid values.
    """
    scores_raw = data.get("scores") or {}

    normalized = {
        "score_overall": _clamp(data.get("score_overall", 0)),
        "scores": {
            "relevance": _clamp(scores_raw.get("relevance", 0)),
            "clarity": _clamp(scores_raw.get("clarity", 0)),
            "specificity": _clamp(scores_raw.get("specificity", 0)),
            "technical_accuracy": _clamp(scores_raw.get("technical_accuracy", 0)),
            "jd_alignment": _clamp(scores_raw.get("jd_alignment", 0)),
            "communication": _clamp(scores_raw.get("communication", 0)),
        },
        "strengths": data.get("strengths") or [],
        "weaknesses": data.get("weaknesses") or [],
        "suggestions": data.get("suggestions") or [],
        "improved_answer_suggestion": data.get("improved_answer_suggestion") or "",
        "short_feedback": data.get("short_feedback") or "",
    }

    for key in ("strengths", "weaknesses", "suggestions"):
        if not isinstance(normalized[key], list):
            normalized[key] = []
        normalized[key] = [str(item) for item in normalized[key]]

    return normalized


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

def evaluate_answer(
    question: str,
    answer: str,
    cv_document,
    jd_document,
    rag_context: list[dict],
    interview_history: str,
) -> dict:
    """
    Evaluate a candidate's answer using LLM.
    """
    cv_json = {}
    jd_json = {}
    try:
        if cv_document and cv_document.parsed_json:
            cv_json = json.loads(cv_document.parsed_json)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        if jd_document and jd_document.parsed_json:
            jd_json = json.loads(jd_document.parsed_json)
    except (json.JSONDecodeError, TypeError):
        pass

    prompt = build_evaluation_prompt(
        question=question,
        answer=answer,
        cv_json=cv_json,
        jd_json=jd_json,
        rag_context=rag_context,
        interview_history=interview_history,
    )

    print("[Evaluation] Calling LLM for answer evaluation...")
    raw_response = generate_text(
        prompt=prompt,
        system_prompt=EVALUATION_SYSTEM_PROMPT,
    )

    evaluation_data = extract_json_from_llm_response(raw_response)
    normalized = normalize_evaluation_json(evaluation_data)
    normalized["_raw_response"] = raw_response

    return normalized
