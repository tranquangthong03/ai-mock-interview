from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def check_and_reset_database():
    """
    [DEMO PHASE ONLY] Check if the database schema matches the models.
    If columns are missing (e.g. parsed_json), drop all tables and recreate.
    In production, use Alembic migrations instead.
    """
    inspector = inspect(engine)

    needs_reset = False

    # Check documents table
    if inspector.has_table("documents"):
        columns = [col["name"] for col in inspector.get_columns("documents")]
        required_columns = {"id", "document_type", "filename", "file_path",
                            "extracted_text", "parsed_json", "created_at"}
        if not required_columns.issubset(set(columns)):
            needs_reset = True
    
    # Check interview tables exist
    if not inspector.has_table("interview_sessions"):
        needs_reset = True
    if not inspector.has_table("interview_messages"):
        needs_reset = True
    else:
        msg_columns = [col["name"] for col in inspector.get_columns("interview_messages")]
        if "audio_file_path" not in msg_columns:
            needs_reset = True
    if not inspector.has_table("answer_evaluations"):
        needs_reset = True
    if not inspector.has_table("interview_reports"):
        needs_reset = True

    if needs_reset:
        print("[WARNING] Database schema outdated or missing tables. Dropping and recreating...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print("[INFO] Database schema is up to date.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()