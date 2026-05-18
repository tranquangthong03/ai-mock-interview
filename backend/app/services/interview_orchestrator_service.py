"""
Interview Orchestrator Service

Generates interview questions using:
  - Parsed CV/JD data
  - RAG context retrieval
  - LLM question generation

This service coordinates the interview flow but does NOT evaluate answers.
"""

import json
from typing import Optional

from app.services.language_policy import (
    CANDIDATE_EXPECTED_LANGUAGE,
    INTERVIEW_QUESTION_LANGUAGE,
)
from app.services.llm_service import generate_text
from app.services.rag_service import retrieve_context


# ---------------------------------------------------------------------------
# Context building helpers
# ---------------------------------------------------------------------------

def _safe_json_str(parsed_json_str: Optional[str], max_chars: int = 3000) -> str:
    """
    Parse a JSON string stored in the DB and return a pretty-printed version
    truncated to *max_chars*. Returns "" if input is None/empty.
    """
    if not parsed_json_str:
        return ""
    try:
        data = json.loads(parsed_json_str)
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        return pretty[:max_chars]
    except (json.JSONDecodeError, TypeError):
        return parsed_json_str[:max_chars]


def build_interview_context(cv_document, jd_document) -> dict:
    """
    Build a context dict with CV and JD info ready for prompt building.
    """
    cv_json_str = _safe_json_str(cv_document.parsed_json)
    jd_json_str = _safe_json_str(jd_document.parsed_json)

    cv_data = {}
    jd_data = {}
    try:
        cv_data = json.loads(cv_document.parsed_json) if cv_document.parsed_json else {}
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        jd_data = json.loads(jd_document.parsed_json) if jd_document.parsed_json else {}
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "cv_json": cv_json_str,
        "jd_json": jd_json_str,
        "cv_text": (cv_document.extracted_text or "")[:2000],
        "jd_text": (jd_document.extracted_text or "")[:2000],
        "target_role": jd_data.get("job_title", cv_data.get("target_role", "")),
        "skills": cv_data.get("skills", []),
        "required_skills": jd_data.get("required_skills", []),
        "experience_level": jd_data.get("experience_level", ""),
        "projects": cv_data.get("projects", []),
        "candidate_name": cv_data.get("candidate_name", ""),
    }


def build_history_text(messages: list, max_messages: int = 20) -> str:
    """
    Convert InterviewMessage ORM objects into readable text for LLM prompts.
    """
    if not messages:
        return "(No interview history yet)"

    lines = []
    for msg in messages[-max_messages:]:
        role_label = {
            "interviewer": "Interviewer",
            "candidate": "Candidate",
            "system": "System",
        }.get(msg.role, msg.role)
        lines.append(f"[Round {msg.round_number}] {role_label}: {msg.content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# RAG query building
# ---------------------------------------------------------------------------

def _build_first_question_query(context: dict) -> str:
    """Build a RAG retrieval query for the first question."""
    parts = []
    if context.get("target_role"):
        parts.append(f"Role: {context['target_role']}")
    if context.get("skills"):
        parts.append(f"Candidate skills: {', '.join(context['skills'][:10])}")
    if context.get("required_skills"):
        parts.append(f"JD requirements: {', '.join(context['required_skills'][:10])}")
    if context.get("projects"):
        project_names = [p.get("name", "") for p in context["projects"][:5] if p.get("name")]
        if project_names:
            parts.append(f"Projects: {', '.join(project_names)}")
    return " | ".join(parts) if parts else "technical interview question"


def _build_followup_query(latest_answer: str, last_question: str, context: dict) -> str:
    """Build a RAG retrieval query for follow-up questions."""
    parts = []
    if latest_answer:
        parts.append(latest_answer[:300])
    if last_question:
        parts.append(last_question[:200])
    if context.get("target_role"):
        parts.append(context["target_role"])
    if context.get("required_skills"):
        parts.append(", ".join(context["required_skills"][:5]))
    return " | ".join(parts) if parts else "follow-up interview question"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

FIRST_QUESTION_SYSTEM_PROMPT = f"""You are a professional technical AI interviewer.
Ask exactly one first interview question for the role the candidate is applying for.

Language policy:
- The interview question language is {INTERVIEW_QUESTION_LANGUAGE}; write the question in English only.
- The candidate is expected to answer in {CANDIDATE_EXPECTED_LANGUAGE}.
- Do not ask Vietnamese questions.
- Do not mix Vietnamese and English unless it is a proper noun, technology name, project name, company name, or quoted CV/JD text.

Question requirements:
- Base the question on the CV, JD, and retrieved context.
- Match the candidate's experience level from the JD.
- Start with a concrete but not overly difficult technical question.
- Do not provide explanations, answers, evaluation, or hints.
- Return only the question text, without prefixes such as "Question:" or numbering."""


FOLLOWUP_SYSTEM_PROMPT = f"""You are a professional technical AI interviewer.
Ask exactly one follow-up interview question based on the CV, JD, retrieved context, interview history, and the candidate's latest answer.

Language policy:
- The follow-up question language is {INTERVIEW_QUESTION_LANGUAGE}; write the question in English only.
- The candidate is expected to answer in {CANDIDATE_EXPECTED_LANGUAGE}.
- Do not ask Vietnamese questions.
- Do not mix Vietnamese and English unless it is a proper noun, technology name, project name, company name, or quoted CV/JD text.

Question requirements:
- Stay close to the candidate's latest answer.
- You may go deeper into a project, technology, design choice, or technical trade-off.
- Do not repeat previous questions.
- Do not evaluate the candidate's answer in this step.
- Do not provide explanations, answers, or hints.
- Return only the question text, without prefixes such as "Question:" or numbering."""


RETRY_SYSTEM_PROMPT = f"""You are an AI interviewer.
The candidate's answer did not address the original question.

Language policy:
- The retry question language is {INTERVIEW_QUESTION_LANGUAGE}; write the question in English only.
- Do not use Vietnamese.

Requirements:
- Ask one short, polite retry question that redirects the candidate back to the original topic.
- Do not provide the answer.
- Do not move to a new topic.
- Return only one question."""


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

def generate_first_question(
    cv_document,
    jd_document,
    interview_type: str = "technical",
) -> str:
    """
    Generate the first personalized interview question in English.
    """
    context = build_interview_context(cv_document, jd_document)

    rag_query = _build_first_question_query(context)
    rag_results = retrieve_context(
        query=rag_query,
        top_k=5,
        document_ids=[cv_document.id, jd_document.id],
    )
    rag_context_text = "\n---\n".join(
        r.get("content", "") for r in rag_results
    ) if rag_results else "(No additional context)"

    user_prompt = f"""Interview type: {interview_type}

CV parsed JSON:
{context['cv_json']}

JD parsed JSON:
{context['jd_json']}

RAG context from CV/JD:
{rag_context_text}

Ask the first interview question now."""

    print(f"[Orchestrator] Generating first question (type={interview_type})")
    question = generate_text(
        prompt=user_prompt,
        system_prompt=FIRST_QUESTION_SYSTEM_PROMPT,
    )

    return question.strip()


def generate_followup_question(
    session,
    messages: list,
    latest_answer: str,
    cv_document,
    jd_document,
) -> str:
    """
    Generate a follow-up question in English based on conversation history.
    """
    context = build_interview_context(cv_document, jd_document)

    last_question = ""
    for msg in reversed(messages):
        if msg.role == "interviewer":
            last_question = msg.content
            break

    rag_query = _build_followup_query(latest_answer, last_question, context)
    rag_results = retrieve_context(
        query=rag_query,
        top_k=5,
        document_ids=[cv_document.id, jd_document.id],
    )
    rag_context_text = "\n---\n".join(
        r.get("content", "") for r in rag_results
    ) if rag_results else "(No additional context)"

    history_text = build_history_text(messages)

    user_prompt = f"""CV parsed JSON:
{context['cv_json']}

JD parsed JSON:
{context['jd_json']}

RAG context:
{rag_context_text}

Interview history:
{history_text}

Candidate's latest answer:
{latest_answer}

Ask the next follow-up question."""

    print(f"[Orchestrator] Generating follow-up question (round={session.current_round})")
    question = generate_text(
        prompt=user_prompt,
        system_prompt=FOLLOWUP_SYSTEM_PROMPT,
    )

    return question.strip()


def generate_retry_question(
    original_question: str,
    candidate_answer: str,
    short_feedback: str = "",
) -> str:
    """
    Generate an English retry/clarification question for low-relevance answers.
    """
    user_prompt = f"""Original question:
{original_question}

Candidate answer that missed the topic:
{candidate_answer}

Evaluation feedback:
{short_feedback or '(none)'}

Ask a retry question that brings the candidate back to the original topic."""

    print("[Orchestrator] Generating retry question (low relevance)")
    question = generate_text(
        prompt=user_prompt,
        system_prompt=RETRY_SYSTEM_PROMPT,
    )

    return question.strip()

