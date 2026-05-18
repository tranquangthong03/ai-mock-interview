from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    parsed_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    cv_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    jd_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    interview_type = Column(String, default="technical")
    target_language = Column(String, default="vi")
    status = Column(String, default="active")  # active | completed
    current_round = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    cv_document = relationship("Document", foreign_keys=[cv_document_id])
    jd_document = relationship("Document", foreign_keys=[jd_document_id])
    messages = relationship(
        "InterviewMessage",
        back_populates="session",
        order_by="InterviewMessage.created_at",
    )
    evaluations = relationship(
        "AnswerEvaluation",
        back_populates="session",
        order_by="AnswerEvaluation.created_at",
    )
    report = relationship(
        "InterviewReport",
        back_populates="session",
        uselist=False,
    )


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # interviewer | candidate | system
    content = Column(Text, nullable=False)
    round_number = Column(Integer, nullable=False)
    audio_file_path = Column(String, nullable=True)       # path to audio file (voice answers)
    speech_metrics_json = Column(Text, nullable=True)      # JSON dict of speech metrics
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    session = relationship("InterviewSession", back_populates="messages")


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_message_id = Column(Integer, ForeignKey("interview_messages.id"), nullable=False)
    answer_message_id = Column(Integer, ForeignKey("interview_messages.id"), nullable=False)
    round_number = Column(Integer, nullable=False)

    # Scores (0–10)
    score_overall = Column(Float, nullable=False, default=0.0)
    relevance_score = Column(Float, nullable=False, default=0.0)
    clarity_score = Column(Float, nullable=False, default=0.0)
    specificity_score = Column(Float, nullable=False, default=0.0)
    technical_accuracy_score = Column(Float, nullable=False, default=0.0)
    jd_alignment_score = Column(Float, nullable=False, default=0.0)
    communication_score = Column(Float, nullable=False, default=0.0)

    # Text feedback (stored as JSON strings for list fields)
    strengths = Column(Text, nullable=True)           # JSON list
    weaknesses = Column(Text, nullable=True)           # JSON list
    suggestions = Column(Text, nullable=True)          # JSON list
    improved_answer_suggestion = Column(Text, nullable=True)
    short_feedback = Column(Text, nullable=True)
    raw_evaluation_json = Column(Text, nullable=True)  # Full raw LLM output

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("InterviewSession", back_populates="evaluations")
    question_message = relationship("InterviewMessage", foreign_keys=[question_message_id])
    answer_message = relationship("InterviewMessage", foreign_keys=[answer_message_id])


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, unique=True)

    overall_score = Column(Float, nullable=False, default=0.0)
    criterion_scores_json = Column(Text, nullable=True)  # JSON dict of average scores
    summary = Column(Text, nullable=True)
    strengths_summary = Column(Text, nullable=True)       # JSON list
    weaknesses_summary = Column(Text, nullable=True)       # JSON list
    skill_gap_summary = Column(Text, nullable=True)        # JSON list
    improvement_plan = Column(Text, nullable=True)         # JSON list
    recommended_topics = Column(Text, nullable=True)       # JSON list
    final_advice = Column(Text, nullable=True)
    raw_report_json = Column(Text, nullable=True)          # Full raw LLM output

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationship
    session = relationship("InterviewSession", back_populates="report")