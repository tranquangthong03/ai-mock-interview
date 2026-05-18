"""
Shared test fixtures for the AI Mock Interviewer test suite.

Provides:
  - In-memory SQLite test database (isolated from app.db)
  - FastAPI TestClient with dependency overrides
  - Mocked LLM service (no real API calls)
  - Mocked RAG service (no real embeddings/ChromaDB)
  - Helper fixtures for creating test data
"""

import json
import pytest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models import Document, InterviewSession, InterviewMessage, AnswerEvaluation, InterviewReport

# ---------------------------------------------------------------------------
# Fake LLM response for evaluation
# ---------------------------------------------------------------------------

FAKE_EVALUATION_JSON = {
    "score_overall": 7.5,
    "scores": {
        "relevance": 8,
        "clarity": 7,
        "specificity": 7,
        "technical_accuracy": 8,
        "jd_alignment": 8,
        "communication": 7,
    },
    "strengths": [
        "Ứng viên trả lời đúng trọng tâm câu hỏi.",
        "Có liên hệ với project trong CV.",
    ],
    "weaknesses": [
        "Chưa giải thích rõ trade-off kỹ thuật.",
        "Thiếu ví dụ về kết quả đạt được.",
    ],
    "suggestions": [
        "Nên trình bày theo cấu trúc bối cảnh - cách làm - kết quả.",
        "Nên bổ sung chi tiết về database hoặc bảo mật.",
    ],
    "improved_answer_suggestion": (
        "Trong project này, em đã xây dựng API đăng nhập bằng FastAPI, "
        "sử dụng JWT để xác thực người dùng. Em thiết kế access token và "
        "refresh token để cân bằng giữa bảo mật và trải nghiệm người dùng..."
    ),
    "short_feedback": (
        "Câu trả lời đúng hướng nhưng cần cụ thể hơn về giải pháp kỹ thuật và kết quả."
    ),
}

FAKE_FOLLOWUP_QUESTION = "Bạn có thể giải thích thêm về cách bạn xử lý refresh token trong project đó không?"

FAKE_REPORT_JSON = {
    "session_id": 1,
    "overall_score": 7.5,
    "criterion_scores": {
        "relevance": 8,
        "clarity": 7,
        "specificity": 7,
        "technical_accuracy": 8,
        "jd_alignment": 8,
        "communication": 7,
    },
    "summary": "Ứng viên có nền tảng phù hợp với vị trí đang ứng tuyển và có thể liên hệ câu trả lời với project trong CV.",
    "strengths_summary": [
        "Trả lời đúng trọng tâm nhiều câu hỏi.",
        "Có liên hệ với project thực tế trong CV.",
    ],
    "weaknesses_summary": [
        "Một số câu trả lời còn thiếu ví dụ cụ thể.",
        "Chưa giải thích rõ trade-off kỹ thuật.",
    ],
    "skill_gap_summary": [
        "Cần ôn thêm về testing và authentication flow.",
        "Cần trình bày rõ hơn về database design.",
    ],
    "improvement_plan": [
        "Luyện trả lời theo cấu trúc STAR hoặc PREP.",
        "Chuẩn bị 2 câu chuyện project có bối cảnh, cách làm và kết quả rõ ràng.",
    ],
    "recommended_topics": [
        "REST API design",
        "JWT authentication",
        "Database indexing",
        "Unit testing",
    ],
    "final_advice": "Ứng viên nên tập trung làm câu trả lời cụ thể hơn, có ví dụ và kết quả rõ ràng hơn.",
}


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///./test_app.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    """Dependency override: use test database."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session():
    """Provide a clean database session for direct DB operations in tests."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """
    FastAPI TestClient with:
      - Test database
      - Mocked LLM (returns fake evaluation JSON or fake follow-up question)
      - Mocked RAG retrieve_context (returns empty list)
    """
    # Import app here to avoid circular imports and ensure overrides take effect
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db

    def fake_generate_text(prompt: str, system_prompt: str = "") -> str:
        """Return fake evaluation JSON, fake report JSON, or fake follow-up question."""
        if "đánh giá" in system_prompt.lower() or "rubric" in prompt.lower():
            return json.dumps(FAKE_EVALUATION_JSON, ensure_ascii=False)
        elif "báo cáo" in system_prompt.lower() or "tổng kết" in system_prompt.lower():
            return json.dumps(FAKE_REPORT_JSON, ensure_ascii=False)
        else:
            return FAKE_FOLLOWUP_QUESTION

    with patch("app.services.answer_evaluation_service.generate_text", side_effect=fake_generate_text), \
         patch("app.services.interview_orchestrator_service.generate_text", side_effect=fake_generate_text), \
         patch("app.services.report_generation_service.generate_text", side_effect=fake_generate_text), \
         patch("app.services.rag_service.get_embedding_model"), \
         patch("app.services.rag_service.get_collection"), \
         patch("app.routers.interviews.retrieve_context", return_value=[]), \
         patch("app.services.interview_orchestrator_service.retrieve_context", return_value=[]):
        with TestClient(app) as tc:
            yield tc

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------

SAMPLE_CV_JSON = json.dumps({
    "candidate_name": "Nguyễn Văn A",
    "target_role": "Backend Developer",
    "education": ["Đại học Bách Khoa - CNTT"],
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "projects": [
        {
            "name": "API Authentication System",
            "role": "Developer",
            "technologies": ["FastAPI", "JWT", "PostgreSQL"],
            "description": "Xây dựng hệ thống xác thực người dùng",
        }
    ],
    "experience": ["Intern tại công ty XYZ"],
    "certifications": [],
}, ensure_ascii=False)

SAMPLE_JD_JSON = json.dumps({
    "job_title": "Junior Backend Developer",
    "company_name": "Tech Corp",
    "experience_level": "Fresher/Junior",
    "required_skills": ["Python", "FastAPI", "SQL", "REST API"],
    "preferred_skills": ["Docker", "Redis"],
    "responsibilities": ["Phát triển API", "Viết unit test"],
    "tools_or_technologies": ["Git", "Docker", "PostgreSQL"],
}, ensure_ascii=False)


@pytest.fixture()
def sample_documents(db_session):
    """Create sample CV and JD documents in the test database."""
    cv_doc = Document(
        document_type="CV",
        filename="test_cv.pdf",
        file_path="/uploads/test_cv.pdf",
        extracted_text="Nguyễn Văn A - Backend Developer - Python, FastAPI",
        parsed_json=SAMPLE_CV_JSON,
    )
    jd_doc = Document(
        document_type="JD",
        filename="test_jd.pdf",
        file_path="/uploads/test_jd.pdf",
        extracted_text="Junior Backend Developer - Python, FastAPI, SQL",
        parsed_json=SAMPLE_JD_JSON,
    )
    db_session.add(cv_doc)
    db_session.add(jd_doc)
    db_session.commit()
    db_session.refresh(cv_doc)
    db_session.refresh(jd_doc)
    return cv_doc, jd_doc


@pytest.fixture()
def sample_session_with_question(db_session, sample_documents):
    """Create a sample interview session with one interviewer question."""
    cv_doc, jd_doc = sample_documents

    session = InterviewSession(
        cv_document_id=cv_doc.id,
        jd_document_id=jd_doc.id,
        interview_type="technical",
        target_language="vi",
        status="active",
        current_round=1,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    question_msg = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content="Bạn hãy mô tả project gần nhất mà bạn đã làm việc với FastAPI?",
        round_number=1,
    )
    db_session.add(question_msg)
    db_session.commit()
    db_session.refresh(question_msg)

    return session, question_msg


@pytest.fixture()
def sample_session_with_evaluations(db_session, sample_documents):
    """Create a session with 2 Q&A rounds and corresponding evaluations."""
    cv_doc, jd_doc = sample_documents

    session = InterviewSession(
        cv_document_id=cv_doc.id,
        jd_document_id=jd_doc.id,
        interview_type="technical",
        target_language="vi",
        status="active",
        current_round=3,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Round 1
    q1 = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content="Bạn hãy mô tả project gần nhất mà bạn đã làm việc với FastAPI?",
        round_number=1,
    )
    a1 = InterviewMessage(
        session_id=session.id,
        role="candidate",
        content="Em đã xây dựng API đăng nhập bằng FastAPI, sử dụng JWT.",
        round_number=1,
    )
    db_session.add_all([q1, a1])
    db_session.commit()
    db_session.refresh(q1)
    db_session.refresh(a1)

    ev1 = AnswerEvaluation(
        session_id=session.id,
        question_message_id=q1.id,
        answer_message_id=a1.id,
        round_number=1,
        score_overall=7.5,
        relevance_score=8,
        clarity_score=7,
        specificity_score=7,
        technical_accuracy_score=8,
        jd_alignment_score=8,
        communication_score=7,
        strengths=json.dumps(["Trả lời đúng trọng tâm."], ensure_ascii=False),
        weaknesses=json.dumps(["Thiếu ví dụ cụ thể."], ensure_ascii=False),
        suggestions=json.dumps(["Nên bổ sung chi tiết hơn."], ensure_ascii=False),
        improved_answer_suggestion="Câu trả lời mẫu tốt hơn.",
        short_feedback="Đúng hướng nhưng cần cụ thể hơn.",
    )

    # Round 2
    q2 = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content="Bạn xử lý refresh token như thế nào?",
        round_number=2,
    )
    a2 = InterviewMessage(
        session_id=session.id,
        role="candidate",
        content="Em dùng refresh token lưu trong httpOnly cookie.",
        round_number=2,
    )
    db_session.add_all([q2, a2])
    db_session.commit()
    db_session.refresh(q2)
    db_session.refresh(a2)

    ev2 = AnswerEvaluation(
        session_id=session.id,
        question_message_id=q2.id,
        answer_message_id=a2.id,
        round_number=2,
        score_overall=6.5,
        relevance_score=7,
        clarity_score=6,
        specificity_score=6,
        technical_accuracy_score=7,
        jd_alignment_score=7,
        communication_score=6,
        strengths=json.dumps(["Biết về httpOnly cookie."], ensure_ascii=False),
        weaknesses=json.dumps(["Chưa nói về token rotation."], ensure_ascii=False),
        suggestions=json.dumps(["Tìm hiểu thêm token rotation."], ensure_ascii=False),
        improved_answer_suggestion="Nên giải thích token rotation.",
        short_feedback="Cần bổ sung kiến thức bảo mật.",
    )

    db_session.add_all([ev1, ev2])
    db_session.commit()

    return session, [q1, a1, q2, a2], [ev1, ev2]
