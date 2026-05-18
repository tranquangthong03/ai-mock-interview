from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import (
    IndexDocumentResponse,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveResultItem,
    RAGStatusResponse,
)
from app.services.rag_service import index_document, retrieve_context, get_status

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/index/{document_id}", response_model=IndexDocumentResponse)
def index_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Index a document into the vector store for RAG retrieval.
    - Chunks the extracted text
    - Creates embeddings using sentence-transformers
    - Stores vectors in ChromaDB
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.extracted_text or not document.extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document has no extracted text. Upload and process the document first.",
        )

    try:
        result = index_document(
            document_id=document.id,
            document_type=document.document_type,
            text=document.extracted_text,
            metadata={"filename": document.filename},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error indexing document: {str(e)}",
        )

    return IndexDocumentResponse(**result)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_context_endpoint(body: RetrieveRequest):
    """
    Retrieve top-k relevant context chunks for a query.
    - Optionally filter by document_ids
    - Returns chunks ranked by cosine similarity
    """
    try:
        raw_results = retrieve_context(
            query=body.query,
            top_k=body.top_k,
            document_ids=body.document_ids,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during retrieval: {str(e)}",
        )

    results = [RetrieveResultItem(**r) for r in raw_results]

    return RetrieveResponse(
        query=body.query,
        top_k=body.top_k,
        results=results,
    )


@router.get("/status", response_model=RAGStatusResponse)
def rag_status_endpoint():
    """
    Check RAG system status: collection info, total chunks, model name.
    """
    try:
        status = get_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking RAG status: {str(e)}",
        )

    return RAGStatusResponse(**status)
