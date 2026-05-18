"""
LLM Extraction Service
Parses extracted document text into structured JSON using LLM.

Delegates actual LLM calls to the shared llm_service module.
"""

import json
import re

from app.services.llm_service import generate_text

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CV_SYSTEM_PROMPT = """You are a CV/Resume parser. Extract structured information from the provided CV text and return ONLY a valid JSON object with the following schema. Do not include any explanation, markdown formatting, or extra text.

JSON Schema:
{
  "candidate_name": "string",
  "target_role": "string",
  "education": ["string"],
  "skills": ["string"],
  "projects": [
    {
      "name": "string",
      "role": "string",
      "technologies": ["string"],
      "description": "string"
    }
  ],
  "experience": ["string"],
  "certifications": ["string"]
}

Rules:
- If a field is not found in the CV, use an empty string for string fields or an empty list for array fields.
- Return ONLY the JSON object, nothing else.
- Do NOT wrap the JSON in markdown code blocks."""

JD_SYSTEM_PROMPT = """You are a Job Description parser. Extract structured information from the provided JD text and return ONLY a valid JSON object with the following schema. Do not include any explanation, markdown formatting, or extra text.

JSON Schema:
{
  "job_title": "string",
  "company_name": "string",
  "experience_level": "string",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "responsibilities": ["string"],
  "tools_or_technologies": ["string"]
}

Rules:
- If a field is not found in the JD, use an empty string for string fields or an empty list for array fields.
- Return ONLY the JSON object, nothing else.
- Do NOT wrap the JSON in markdown code blocks."""


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def extract_json_from_response(response_text: str) -> dict:
    """
    Try to parse JSON from LLM response.
    Handles cases where LLM wraps JSON in markdown code blocks or adds extra text.
    """
    text = response_text.strip()

    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract from markdown code block ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Attempt 3: find first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract valid JSON from LLM response. Raw response:\n{text[:500]}"
    )


def _get_llm_response(system_prompt: str, user_text: str) -> str:
    """Route the call to the shared LLM service."""
    return generate_text(prompt=user_text, system_prompt=system_prompt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_cv_text(text: str) -> dict:
    """Parse CV text into structured JSON using LLM."""
    raw_response = _get_llm_response(CV_SYSTEM_PROMPT, text)
    return extract_json_from_response(raw_response)


def parse_jd_text(text: str) -> dict:
    """Parse JD text into structured JSON using LLM."""
    raw_response = _get_llm_response(JD_SYSTEM_PROMPT, text)
    return extract_json_from_response(raw_response)


def parse_document(document_type: str, text: str) -> dict:
    """
    Parse document text based on type.

    Args:
        document_type: "CV" or "JD"
        text: extracted plain text from the document

    Returns:
        Structured dict parsed from LLM response
    """
    if document_type == "CV":
        return parse_cv_text(text)
    elif document_type == "JD":
        return parse_jd_text(text)
    else:
        raise ValueError(f"Unsupported document_type: {document_type}. Must be 'CV' or 'JD'.")
