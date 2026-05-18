import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListItemResponse,
    ParseResponse,
)
from app.services.document_service import extract_text
from app.services.llm_extraction_service import parse_document

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_file_extension(filename: str) -> None:
    """Validate file extension"""
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only PDF, DOCX, TXT are supported. Got: {file_ext}"
        )


@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    document_type: str = Form(...),  # CV hoặc JD
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document (CV or JD)
    - **document_type**: Must be "CV" or "JD"
    - **file**: PDF, DOCX, or TXT file
    """
    # Validate document_type
    if document_type not in ["CV", "JD"]:
        raise HTTPException(
            status_code=400,
            detail="document_type must be CV or JD"
        )

    # Validate file extension
    validate_file_extension(file.filename)

    # Save file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text
    try:
        extracted_text = extract_text(str(file_path))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

    # Save to database
    document = Document(
        document_type=document_type,
        filename=file.filename,
        file_path=str(file_path),
        extracted_text=extracted_text,
        parsed_json=None  # Will be filled by CV/JD Extractor later
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Return response matching DocumentResponse schema
    return DocumentResponse(
        id=document.id,
        document_type=document.document_type,
        filename=document.filename,
        extracted_text_preview=extracted_text[:1000] if extracted_text else "",
        text_length=len(extracted_text) if extracted_text else 0,
        message=f"Document '{file.filename}' uploaded and processed successfully"
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get a specific document by ID
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("", response_model=list[DocumentListItemResponse])
def list_documents(
    document_type: str = Query(None, description="Filter by document type: CV or JD"),
    db: Session = Depends(get_db)
):
    """
    Get list of all documents with optional filter by document_type
    - **document_type** (optional): Filter by "CV" or "JD"
    """
    query = db.query(Document)
    
    if document_type:
        if document_type not in ["CV", "JD"]:
            raise HTTPException(
                status_code=400,
                detail="document_type must be CV or JD"
            )
        query = query.filter(Document.document_type == document_type)
    
    documents = query.order_by(Document.created_at.desc()).all()
    
    # Return list of DocumentListItemResponse
    result = [
        DocumentListItemResponse(
            id=doc.id,
            document_type=doc.document_type,
            filename=doc.filename,
            text_length=len(doc.extracted_text) if doc.extracted_text else 0,
            created_at=doc.created_at
        )
        for doc in documents
    ]
    
    return result


@router.post("/{document_id}/parse", response_model=ParseResponse)
def parse_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Parse a document's extracted text into structured JSON using LLM.
    - **document_id**: ID of the uploaded document
    - Uses LLM to extract structured data from CV or JD text
    - Saves the result in parsed_json field
    """
    # Find document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if extracted_text exists
    if not document.extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Document has no extracted text. Please re-upload the document."
        )

    # Call LLM to parse
    try:
        parsed_data = parse_document(document.document_type, document.extracted_text)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM returned invalid JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during LLM parsing: {str(e)}"
        )

    # Save parsed_json to database
    document.parsed_json = json.dumps(parsed_data, ensure_ascii=False)
    db.commit()
    db.refresh(document)

    return ParseResponse(
        id=document.id,
        document_type=document.document_type,
        filename=document.filename,
        parsed_json=parsed_data,
        message=f"Document '{document.filename}' parsed successfully"
    )