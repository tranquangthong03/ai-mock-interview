"""
RAG Service - Chunking, Embedding, Indexing & Retrieval

Handles:
  - Text chunking with overlap
  - Embedding via sentence-transformers (local, free)
  - Vector storage in ChromaDB (local, persistent)
  - Top-k context retrieval with optional document filtering

Environment variables:
  EMBEDDING_MODEL_NAME  (default: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
  CHROMA_DB_PATH        (default: chroma_db)
  CHROMA_COLLECTION     (default: interview_documents)
"""

import os
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "interview_documents")

# ---------------------------------------------------------------------------
# Singletons (lazy-loaded)
# ---------------------------------------------------------------------------

_embedding_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.ClientAPI] = None


def get_embedding_model() -> SentenceTransformer:
    """Return a cached SentenceTransformer instance."""
    global _embedding_model
    if _embedding_model is None:
        print(f"[RAG] Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print(f"[RAG] Embedding model loaded successfully.")
    return _embedding_model


def get_chroma_client() -> chromadb.ClientAPI:
    """Return a cached persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        print(f"[RAG] ChromaDB client initialised at: {CHROMA_DB_PATH}")
    return _chroma_client


def get_collection() -> chromadb.Collection:
    """Return (or create) the interview_documents collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Text Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 700,
    chunk_overlap: int = 120,
) -> list[str]:
    """
    Split *text* into overlapping chunks.

    - Works well with Vietnamese text (character-level splitting).
    - Strips whitespace per chunk, drops empties.
    - If the text is shorter than *chunk_size*, returns a single chunk.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        # Advance by (chunk_size - overlap) so consecutive chunks share
        # *chunk_overlap* characters of context.
        start += chunk_size - chunk_overlap

    return chunks


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_document(
    document_id: int,
    document_type: str,
    text: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Chunk *text*, embed every chunk and upsert into ChromaDB.

    Returns a summary dict with chunk count etc.
    """
    metadata = metadata or {}

    # 1. Chunk
    chunks = chunk_text(text)
    if not chunks:
        return {
            "document_id": document_id,
            "document_type": document_type,
            "chunks_indexed": 0,
            "collection": CHROMA_COLLECTION,
            "message": "No chunks produced (text may be empty)",
        }

    # 2. Embed
    model = get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    # 3. Prepare ChromaDB payload
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    now_str = datetime.now(timezone.utc).isoformat()

    for idx, chunk in enumerate(chunks):
        chunk_id = f"document_{document_id}_chunk_{idx}"
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "document_id": document_id,
            "document_type": document_type,
            "chunk_index": idx,
            "source": metadata.get("filename", ""),
            "text_preview": chunk[:120],
            "created_at": now_str,
        })

    # 4. Upsert (idempotent – re-indexing the same doc overwrites)
    collection = get_collection()
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return {
        "document_id": document_id,
        "document_type": document_type,
        "chunks_indexed": len(chunks),
        "collection": CHROMA_COLLECTION,
        "message": "Document indexed successfully",
    }


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_context(
    query: str,
    top_k: int = 5,
    document_ids: Optional[list[int]] = None,
) -> list[dict]:
    """
    Retrieve the *top_k* most relevant chunks for *query*.

    If *document_ids* is supplied, only chunks belonging to those documents
    are considered.

    Returns a list of dicts with content, score (cosine similarity) and
    metadata.
    """
    model = get_embedding_model()
    query_embedding = model.encode([query], show_progress_bar=False).tolist()

    collection = get_collection()

    # Build optional where-filter
    where_filter = None
    if document_ids:
        if len(document_ids) == 1:
            where_filter = {"document_id": document_ids[0]}
        else:
            where_filter = {"document_id": {"$in": document_ids}}

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # ChromaDB returns lists-of-lists; flatten the first (and only) query.
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output: list[dict] = []
    for doc, meta, dist in zip(docs, metas, distances):
        # ChromaDB cosine distance = 1 - cosine_similarity
        similarity = round(1.0 - dist, 4)
        output.append({
            "document_id": meta.get("document_id"),
            "document_type": meta.get("document_type"),
            "chunk_index": meta.get("chunk_index"),
            "content": doc,
            "score": similarity,
            "metadata": meta,
        })

    return output


# ---------------------------------------------------------------------------
# Status helper
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """Return current RAG system status."""
    collection = get_collection()
    return {
        "collection": CHROMA_COLLECTION,
        "total_chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "vector_store_path": CHROMA_DB_PATH,
    }
