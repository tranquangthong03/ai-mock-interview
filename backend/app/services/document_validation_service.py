import os
import re


CV_HINTS = (
    "experience",
    "education",
    "skills",
    "project",
    "summary",
    "employment",
    "work history",
)

JD_HINTS = (
    "requirements",
    "responsibilities",
    "qualifications",
    "role",
    "skills",
    "experience",
    "job description",
    "we are looking",
)

VIETNAMESE_CHARS_RE = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE)
EN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _min_words() -> int:
    return int(os.getenv("DOCUMENT_MIN_WORDS", "40"))


def _max_vietnamese_char_ratio() -> float:
    return float(os.getenv("DOCUMENT_MAX_VI_CHAR_RATIO", "0.03"))


def _count_words(text: str) -> int:
    return len(EN_WORD_RE.findall(text))


def validate_document_for_parse(document_type: str, extracted_text: str) -> None:
    text = (extracted_text or "").strip()
    if not text:
        raise ValueError("Document text is empty.")

    word_count = _count_words(text)
    if word_count < _min_words():
        raise ValueError(
            f"Document content is too short for reliable parsing (minimum {_min_words()} English words)."
        )

    vi_chars = len(VIETNAMESE_CHARS_RE.findall(text))
    letter_chars = len(re.findall(r"[A-Za-zÀ-ỹà-ỹ]", text))
    if letter_chars > 0:
        vi_ratio = vi_chars / letter_chars
        if vi_ratio > _max_vietnamese_char_ratio():
            raise ValueError(
                "Document appears to be non-English. Please upload an English CV/JD for best interview quality."
            )

    lowered = text.lower()
    hints = CV_HINTS if document_type == "CV" else JD_HINTS if document_type == "JD" else ()
    if hints and not any(hint in lowered for hint in hints):
        raise ValueError(
            f"Document does not look like a valid {document_type}. "
            f"Please upload a clearer {document_type} with standard section headings."
        )
