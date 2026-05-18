from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional

class DocumentBase(BaseModel):
    filename: str
    document_type: str
    file_path: str
    extracted_text: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(BaseModel):
    id: int
    document_type: str
    filename: str
    extracted_text_preview: str
    text_length: int
    message: str

    class Config:
        from_attributes = True

class DocumentDetailResponse(BaseModel):
    id: int
    document_type: str
    filename: str
    file_path: str
    extracted_text: Optional[str] = None
    parsed_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentListItemResponse(BaseModel):
    id: int
    document_type: str
    filename: str
    text_length: int
    created_at: datetime

    class Config:
        from_attributes = True


class ParseResponse(BaseModel):
    id: int
    document_type: str
    filename: str
    parsed_json: Any
    message: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# RAG Schemas
# ---------------------------------------------------------------------------

class IndexDocumentResponse(BaseModel):
    document_id: int
    document_type: str
    chunks_indexed: int
    collection: str
    message: str


class RetrieveResultItem(BaseModel):
    document_id: int
    document_type: str
    chunk_index: int
    content: str
    score: float
    metadata: dict


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    document_ids: Optional[list[int]] = None


class RetrieveResponse(BaseModel):
    query: str
    top_k: int
    results: list[RetrieveResultItem]


class RAGStatusResponse(BaseModel):
    collection: str
    total_chunks: int
    embedding_model: str
    vector_store_path: str


# ---------------------------------------------------------------------------
# Interview Schemas
# ---------------------------------------------------------------------------

class StartInterviewRequest(BaseModel):
    cv_document_id: int
    jd_document_id: int
    interview_type: str = "technical"
    target_language: str = "vi"


class StartInterviewResponse(BaseModel):
    session_id: int
    status: str
    first_question: str
    round_number: int


class SubmitAnswerRequest(BaseModel):
    answer: str


class SubmitAnswerResponse(BaseModel):
    session_id: int
    round_number: int
    candidate_answer: str
    evaluation: Optional["EvaluationResult"] = None
    next_question: str
    status: str


class InterviewMessageItem(BaseModel):
    id: int
    role: str
    content: str
    round_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewHistoryResponse(BaseModel):
    session_id: int
    cv_document_id: int
    jd_document_id: int
    interview_type: str
    status: str
    current_round: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    messages: list[InterviewMessageItem]


class EndInterviewResponse(BaseModel):
    session_id: int
    status: str
    total_rounds: int
    message: str


# ---------------------------------------------------------------------------
# Speech / Audio Schemas
# ---------------------------------------------------------------------------

class SpeechMetrics(BaseModel):
    duration_seconds: float = 0
    word_count: int = 0
    speech_rate_wpm: float = 0
    filler_words: list[str] = []
    filler_word_count: int = 0
    estimated_pause_count: int = 0
    notes: list[str] = []


class SubmitAudioAnswerResponse(BaseModel):
    session_id: int
    round_number: int
    transcript: str
    speech_metrics: SpeechMetrics
    evaluation: Optional["EvaluationResult"] = None
    next_question: str
    status: str


class TranscribeAudioResponse(BaseModel):
    session_id: int
    transcript: str
    speech_metrics: SpeechMetrics
    audio_file_path: str


# ---------------------------------------------------------------------------
# Answer Evaluation Schemas
# ---------------------------------------------------------------------------

class EvaluationScores(BaseModel):
    relevance: float = 0.0
    clarity: float = 0.0
    specificity: float = 0.0
    technical_accuracy: float = 0.0
    jd_alignment: float = 0.0
    communication: float = 0.0


class EvaluationResult(BaseModel):
    score_overall: float = 0.0
    scores: EvaluationScores = EvaluationScores()
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []
    improved_answer_suggestion: str = ""
    short_feedback: str = ""


class EvaluationListItem(BaseModel):
    id: int
    round_number: int
    question: str
    answer: str
    score_overall: float
    scores: EvaluationScores
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    improved_answer_suggestion: str
    short_feedback: str
    created_at: datetime


class SessionEvaluationsResponse(BaseModel):
    session_id: int
    evaluations: list[EvaluationListItem]


# ---------------------------------------------------------------------------
# Interview Report Schemas
# ---------------------------------------------------------------------------

class InterviewSummaryResponse(BaseModel):
    session_id: int
    total_answers: int
    average_score: float
    criterion_averages: dict
    best_criterion: str
    weakest_criterion: str


class GenerateReportResponse(BaseModel):
    session_id: int
    overall_score: float
    criterion_scores: dict
    summary: str
    strengths_summary: list[str]
    weaknesses_summary: list[str]
    skill_gap_summary: list[str]
    improvement_plan: list[str]
    recommended_topics: list[str]
    final_advice: str
    message: str


class InterviewReportResponse(BaseModel):
    session_id: int
    overall_score: float
    criterion_scores: dict
    summary: str
    strengths_summary: list[str]
    weaknesses_summary: list[str]
    skill_gap_summary: list[str]
    improvement_plan: list[str]
    recommended_topics: list[str]
    final_advice: str
    created_at: datetime
    updated_at: Optional[datetime] = None
