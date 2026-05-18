# AI Mock Interviewer API Documentation

## 1. API Overview

This API powers the AI Mock Interviewer backend.  
It supports the full workflow: upload CV/JD, parse documents, index/retrieve RAG context, start interview sessions, submit text/audio answers, evaluate answers, generate reports, and export reports (Markdown/PDF).

## 2. Base URL

- Local development: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## 3. Authentication

Current version does not require authentication.  
Authentication/user accounts are planned for future work.

## 4. Response Format

- Primary format: JSON (`application/json`)
- File export responses:
  - Markdown: `text/markdown`
  - PDF: `application/pdf`
- Typical error shape:
  ```json
  {
    "detail": "Error message"
  }
  ```
- Common status codes:
  - `200` OK
  - `400` Bad Request
  - `404` Not Found
  - `422` Validation Error
  - `500` Internal Server Error

## 5. Endpoint Summary Table

| Method | Endpoint | Description | Request Type | Response |
|---|---|---|---|---|
| GET | `/` | Health/root info | None | JSON |
| POST | `/documents/upload` | Upload CV/JD and extract text | `multipart/form-data` | `DocumentResponse` |
| GET | `/documents` | List documents (optional type filter) | Query params | `DocumentListItemResponse[]` |
| GET | `/documents/{document_id}` | Get document detail | Path param | `DocumentDetailResponse` |
| POST | `/documents/{document_id}/parse` | Parse document text into structured JSON via LLM | Path param | `ParseResponse` |
| POST | `/rag/index/{document_id}` | Index document into ChromaDB | Path param | `IndexDocumentResponse` |
| POST | `/rag/retrieve` | Retrieve top-k relevant chunks | JSON | `RetrieveResponse` |
| GET | `/rag/status` | Get RAG collection status | None | `RAGStatusResponse` |
| POST | `/interviews/start` | Start interview session and generate first question | JSON | `StartInterviewResponse` |
| POST | `/interviews/{session_id}/answer` | Submit text answer, evaluate, generate next question | JSON + path | `SubmitAnswerResponse` |
| POST | `/interviews/{session_id}/answer-audio` | Submit audio answer, transcribe, evaluate, next question | `multipart/form-data` + path | `SubmitAudioAnswerResponse` |
| POST | `/interviews/{session_id}/transcribe-audio` | Transcribe audio only (no evaluation) | `multipart/form-data` + path | `TranscribeAudioResponse` |
| GET | `/interviews/{session_id}` | Get interview history/messages | Path param | `InterviewHistoryResponse` |
| GET | `/interviews/{session_id}/evaluations` | Get all evaluation results for session | Path param | `SessionEvaluationsResponse` |
| POST | `/interviews/{session_id}/end` | End interview session | Path param | `EndInterviewResponse` |
| GET | `/interviews/{session_id}/summary` | Compute summary stats from evaluations | Path param | `InterviewSummaryResponse` |
| POST | `/interviews/{session_id}/report` | Generate or update interview report | Path param | `GenerateReportResponse` |
| GET | `/interviews/{session_id}/report` | Get saved report | Path param | `InterviewReportResponse` |
| GET | `/interviews/{session_id}/report/export` | Export saved report as Markdown/PDF | Path + query (`format`) | Markdown/PDF file |

## 6. Detailed Endpoint Documentation

### GET `/`
- Purpose: Root health/info endpoint.
- Response: `message`, `stt_provider`, `ffmpeg_available`
- Success: `200`
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/"
```

### POST `/documents/upload`
- Purpose: Upload CV/JD file and extract text.
- Content-Type: `multipart/form-data`
- Form fields:
  - `document_type` (`CV` or `JD`)
  - `file` (supported: `.pdf`, `.docx`, `.txt`)
- Response: `DocumentResponse`
- Success: `200`
- Errors: `400` invalid `document_type` or unsupported file; `500` processing error
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "document_type=CV" \
  -F "file=@sample_cv.pdf"
```

### GET `/documents`
- Purpose: List documents.
- Query params:
  - `document_type` (optional, `CV` or `JD`)
- Response: `DocumentListItemResponse[]`
- Success: `200`
- Errors: `400` invalid `document_type`
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/documents?document_type=CV"
```

### GET `/documents/{document_id}`
- Purpose: Get a document by ID.
- Path params: `document_id` (int)
- Response: `DocumentDetailResponse`
- Success: `200`
- Errors: `404` document not found
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/documents/1"
```

### POST `/documents/{document_id}/parse`
- Purpose: Parse extracted text to structured JSON using LLM.
- Path params: `document_id` (int)
- Request body: none
- Response: `ParseResponse`
- Success: `200`
- Errors: `404` not found; `400` no extracted text; `500` LLM/env/connection/parsing errors
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/documents/1/parse"
```

### POST `/rag/index/{document_id}`
- Purpose: Chunk + embed + index document in ChromaDB.
- Path params: `document_id` (int)
- Request body: none
- Response: `IndexDocumentResponse`
- Success: `200`
- Errors: `404` not found; `400` empty extracted text; `500` indexing error
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/rag/index/1"
```

### POST `/rag/retrieve`
- Purpose: Retrieve top-k relevant context chunks.
- Request body (JSON):
  - `query` (string)
  - `top_k` (int, default `5`)
  - `document_ids` (optional `int[]`)
- Response: `RetrieveResponse`
- Success: `200`
- Errors: `500` retrieval error
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/rag/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"python backend\",\"top_k\":5,\"document_ids\":[1,2]}"
```

### GET `/rag/status`
- Purpose: Get RAG system status.
- Response: `collection`, `total_chunks`, `embedding_model`, `vector_store_path`
- Success: `200`
- Errors: `500`
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/rag/status"
```

### POST `/interviews/start`
- Purpose: Start a new interview session and generate first question.
- Request body (JSON):
  - `cv_document_id` (int)
  - `jd_document_id` (int)
  - `interview_type` (string, default `technical`)
  - `target_language` (string, default `vi`)
- Response: `StartInterviewResponse`
- Success: `200`
- Errors: `404` document not found; `400` wrong type/not parsed; `500` question generation error
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/start" \
  -H "Content-Type: application/json" \
  -d "{\"cv_document_id\":1,\"jd_document_id\":2,\"interview_type\":\"technical\",\"target_language\":\"vi\"}"
```

### POST `/interviews/{session_id}/answer`
- Purpose: Submit text answer, evaluate, and get next question.
- Path params: `session_id` (int)
- Request body: `{ "answer": "..." }`
- Response: `SubmitAnswerResponse`
- Success: `200`
- Errors: `404` session not found; `400` session completed/empty answer/no question; `500` generation/evaluation pipeline errors
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/1/answer" \
  -H "Content-Type: application/json" \
  -d "{\"answer\":\"I optimized API latency by adding async I/O and caching.\"}"
```

### POST `/interviews/{session_id}/answer-audio`
- Purpose: Submit voice answer (save audio, transcribe, evaluate, next question).
- Path params: `session_id` (int)
- Content-Type: `multipart/form-data`
- Form fields:
  - `audio_file` (audio upload)
- Response: `SubmitAudioAnswerResponse`
- Success: `200`
- Errors: `404` session not found; `400` invalid/completed session/audio validation; `500` unexpected processing errors
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/1/answer-audio" \
  -F "audio_file=@answer.wav"
```

### POST `/interviews/{session_id}/transcribe-audio`
- Purpose: Transcribe audio only (no evaluation, no new interview message).
- Path params: `session_id` (int)
- Content-Type: `multipart/form-data`
- Form fields:
  - `audio_file` (audio upload)
- Response: `TranscribeAudioResponse`
- Success: `200`
- Errors: `404` session not found; `400` completed/invalid audio; `500` processing errors
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/1/transcribe-audio" \
  -F "audio_file=@answer.wav"
```

### GET `/interviews/{session_id}`
- Purpose: Get full interview history and messages.
- Path params: `session_id` (int)
- Response: `InterviewHistoryResponse`
- Success: `200`
- Errors: `404` session not found
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1"
```

### GET `/interviews/{session_id}/evaluations`
- Purpose: Get all answer evaluations in a session.
- Path params: `session_id` (int)
- Response: `SessionEvaluationsResponse`
- Success: `200`
- Errors: `404` session not found
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1/evaluations"
```

### POST `/interviews/{session_id}/end`
- Purpose: Mark interview session as completed.
- Path params: `session_id` (int)
- Request body: none
- Response: `EndInterviewResponse`
- Success: `200`
- Errors: `404` session not found; `400` already completed
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/1/end"
```

### GET `/interviews/{session_id}/summary`
- Purpose: Return score summary computed from evaluations (no LLM call).
- Path params: `session_id` (int)
- Response: `InterviewSummaryResponse`
- Success: `200`
- Errors: `404` session not found
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1/summary"
```

### POST `/interviews/{session_id}/report`
- Purpose: Generate or update final interview report for a session.
- Path params: `session_id` (int)
- Request body: none
- Response: `GenerateReportResponse`
- Success: `200`
- Errors: `404` session not found; `400` no evaluations; `500` report generation error
- Example:
```bash
curl -X POST "http://127.0.0.1:8000/interviews/1/report"
```

### GET `/interviews/{session_id}/report`
- Purpose: Retrieve saved interview report.
- Path params: `session_id` (int)
- Response: `InterviewReportResponse`
- Success: `200`
- Errors: `404` session/report not found
- Example:
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1/report"
```

### GET `/interviews/{session_id}/report/export`
- Purpose: Export existing report as Markdown or PDF.
- Path params: `session_id` (int)
- Query params:
  - `format` (required): `markdown` or `pdf`
- Response:
  - Markdown file (`.md`) or PDF file (`.pdf`)
- Success: `200`
- Errors: `400` invalid format; `404` no saved report
- Example (Markdown):
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1/report/export?format=markdown" -o report.md
```
- Example (PDF):
```bash
curl -X GET "http://127.0.0.1:8000/interviews/1/report/export?format=pdf" -o report.pdf
```

---

## Notes

- Source of truth used for this document: backend router + schema code under `backend/app/main.py`, `backend/app/routers/*`, `backend/app/schemas.py`, and model constraints in `backend/app/models.py`.
- No endpoints were inferred without code evidence.
