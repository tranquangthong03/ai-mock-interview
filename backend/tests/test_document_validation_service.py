import pytest

from app.services.document_validation_service import validate_document_for_parse


def test_validate_document_for_parse_accepts_cv_english():
    text = """
    John Doe
    Professional Summary
    Backend engineer with 3 years of experience building REST APIs and microservices.
    Skills: Python, FastAPI, SQLAlchemy, PostgreSQL, Docker, CI/CD
    Work Experience
    - Built authentication and report export modules
    Education
    BSc in Computer Science
    Projects
    AI mock interview platform with RAG indexing and evaluation.
    """
    validate_document_for_parse("CV", text)


def test_validate_document_for_parse_rejects_short_text():
    with pytest.raises(ValueError, match="too short"):
        validate_document_for_parse("CV", "Python developer CV")


def test_validate_document_for_parse_rejects_wrong_structure_for_jd():
    text = """
    Team dinner photos and random notes.
    This memo documents event planning details, booking updates, food options,
    volunteer checklists, and timelines for next month activities. It includes
    reminders for attendance, decoration setup, venue entry points, safety checks,
    and transportation coordination. It does not define a software position,
    does not include technical hiring criteria, and does not describe engineering
    expectations in a structured format suitable for interview preparation.
    """
    with pytest.raises(ValueError, match="does not look like a valid JD"):
        validate_document_for_parse("JD", text)


def test_validate_document_for_parse_rejects_non_english_text():
    text = """
    Kinh nghiệm làm việc:
    Tôi đã làm việc trong nhiều dự án backend cho thương mại điện tử và giáo dục.
    Kỹ năng: Python, FastAPI, SQL, Docker, Redis, giao tiếp nhóm, quản lý thời gian.
    Mục tiêu nghề nghiệp: phát triển hệ thống ổn định, mở rộng tốt và dễ bảo trì.
    Thành tích: tối ưu truy vấn, giảm độ trễ, tăng độ tin cậy dịch vụ trong môi trường thực tế.
    Dự án: xây dựng API, viết kiểm thử, thiết kế cơ sở dữ liệu, triển khai CI/CD và giám sát.
    """
    with pytest.raises(ValueError, match="non-English"):
        validate_document_for_parse("CV", text)
