# AI Mock Interviewer - Backend

A FastAPI-based backend for the AI Mock Interviewer application.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   └── documents.py     # Document endpoints
│   └── services/
│       └── document_service.py  # Business logic for documents
├── uploads/                 # Directory for uploaded files
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Features

- Document upload and management
- RESTful API endpoints
- SQLite database
- CORS support
- Interactive API documentation (Swagger UI)

## API Endpoints

- `GET /api/documents` - List all documents
- `GET /api/documents/{document_id}` - Get a specific document
- `POST /api/documents/upload` - Upload a new document
- `DELETE /api/documents/{document_id}` - Delete a document
