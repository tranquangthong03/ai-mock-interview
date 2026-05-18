# AI Mock Interviewer

Hệ thống luyện phỏng vấn kỹ thuật với AI — đánh giá chi tiết theo 6 tiêu chí và kế hoạch cải thiện cá nhân hóa.

## Kiến trúc

```
Frontend (Next.js)  →  Backend (FastAPI)  →  AI/RAG  →  Database
     :3000                  :8000           Gemini      SQLite
                                           ChromaDB
```

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js 16, React, TypeScript, Tailwind CSS |
| Backend | Python 3.13, FastAPI, SQLAlchemy |
| AI | Google Gemini (qua API key) |
| Vector Store | ChromaDB + SentenceTransformers |
| Database | SQLite (local) |
| Tests | pytest (backend), npm run build (frontend) |

## Tính năng

1. **Document Management** — Upload/Parse/Index CV & JD
2. **RAG Module** — Chunking, Embedding, Semantic Retrieval
3. **Interview Orchestration** — Tạo session, Q&A với AI
4. **Answer Evaluation** — Đánh giá theo 6 tiêu chí, feedback tiếng Việt
5. **Interview Report** — Báo cáo tổng kết, skill gaps, kế hoạch cải thiện
6. **Voice Input** — Ghi âm trả lời, Speech-to-Text, speech metrics
7. **Text-to-Speech** — Đọc câu hỏi AI bằng giọng nói browser
8. **Export Report** — Tải báo cáo dưới dạng Markdown (.md) hoặc PDF (.pdf)
9. **Frontend MVP** — Giao diện web hoàn chỉnh cho demo

## Cài đặt & Chạy

### 1. Backend

```bash
cd backend

# Tạo virtual environment (lần đầu)
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1    # Windows PowerShell
# source venv/bin/activate     # Linux/Mac

# Cài dependencies
pip install -r requirements.txt

# Cấu hình .env
# Tạo file backend/.env với nội dung:
#   LLM_PROVIDER=gemini
#   GEMINI_API_KEY=your_api_key_here
#   STT_PROVIDER=mock        # mock | whisper | faster-whisper
#   WHISPER_MODEL=base.en    # base.en | small.en recommended for English answers
#   INTERVIEW_QUESTION_LANGUAGE=en
#   CANDIDATE_EXPECTED_LANGUAGE=en
#   FEEDBACK_LANGUAGE=vi
#   REPORT_LANGUAGE=vi
#   STT_LANGUAGE=en

# (Optional) Nếu muốn STT thật:
# pip install faster-whisper
# Sửa STT_PROVIDER=faster-whisper trong .env

# Chạy server
uvicorn app.main:app --reload
```

Backend chạy tại: **http://localhost:8000**
Swagger UI: **http://localhost:8000/docs**

### 2. Frontend

```bash
cd frontend

# Cài dependencies (lần đầu)
npm install

# Cấu hình .env.local (đã có sẵn)
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Chạy dev server
npm run dev
```

Frontend chạy tại: **http://localhost:3000**

## Demo Workflow

### Chuẩn bị
1. Chạy backend (`uvicorn app.main:app --reload`)
2. Chạy frontend (`npm run dev`)
3. Mở **http://localhost:3000**

### Flow demo (10 phút)

| Bước | Hành động | Trang |
|------|-----------|-------|
| 1 | Nhấn "Bắt đầu Demo" | `/` |
| 2 | Tải sample CV (hoặc file riêng) | `/setup` |
| 3 | Upload CV → Parse → Index | `/setup` |
| 4 | Tải sample JD (hoặc file riêng) | `/setup` |
| 5 | Upload JD → Parse → Index | `/setup` |
| 6 | Start Interview | `/setup` |
| 7 | Trả lời câu hỏi AI (2-3 lần) | `/interview/[id]` |
| 8 | Xem evaluation sau mỗi câu | `/interview/[id]` |
| 9 | Kết thúc phỏng vấn | `/interview/[id]` |
| 10 | Generate Report → Xem kết quả | `/report/[id]` |

### Sample Files

Có sẵn trong `frontend/public/demo_samples/`:
- `sample_cv_backend_intern.txt` — CV ứng viên Backend Intern
- `sample_jd_backend_intern.txt` — JD vị trí Backend Intern

Tải trực tiếp từ UI hoặc download tại:
- http://localhost:3000/demo_samples/sample_cv_backend_intern.txt
- http://localhost:3000/demo_samples/sample_jd_backend_intern.txt

## Tests

### Backend
```bash
cd backend
.\venv\Scripts\Activate.ps1
pytest -q
# Expected: 72 passed
```

### Frontend
```bash
cd frontend
npm run build
# Expected: Build successful, no TypeScript errors
```

## Cấu trúc dự án

```
ai-mock-interviewer/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── routers/
│   │   │   ├── documents.py
│   │   │   ├── rag.py
│   │   │   ├── interviews.py
│   │   │   └── reports.py
│   │   └── services/
│   │       ├── llm_service.py
│   │       ├── llm_extraction_service.py
│   │       ├── document_service.py
│   │       ├── rag_service.py
│   │       ├── interview_orchestrator_service.py
│   │       ├── answer_evaluation_service.py
│   │       ├── report_generation_service.py
│   │       └── audio_processing_service.py
│   ├── tests/
│   ├── uploads/audio/      # Voice answer files
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # Reusable UI (SpeechMetricsCard, etc.)
│   │   ├── lib/           # API client, helpers
│   │   └── types/         # TypeScript types
│   ├── public/
│   │   └── demo_samples/  # Sample CV/JD
│   └── .env.local
├── README.md
├── E2E_CHECKLIST.md
└── DEMO_GUIDE.md
```

## Voice Input/Output

### Cách dùng Voice Answer
1. Trên trang phỏng vấn, chuyển sang tab "🎙️ Trả lời bằng giọng nói"
2. Nhấn "Bắt đầu ghi âm" → cấp quyền microphone
3. Nói câu trả lời → nhấn "Dừng ghi âm"
4. Nghe lại bằng audio preview
5. Nhấn "Gửi câu trả lời bằng giọng nói"
6. Kết quả: transcript, speech metrics, evaluation

### Speech-to-Text (STT)
- **Mock mode** (mặc định): `STT_PROVIDER=mock` — trả transcript giả, không cần cài thêm gì
- **Faster-whisper**: `pip install faster-whisper` + `STT_PROVIDER=faster-whisper`
- **OpenAI Whisper**: `pip install openai-whisper` + `STT_PROVIDER=whisper`
- **English STT**: đặt `STT_LANGUAGE=en` và ưu tiên `WHISPER_MODEL=base.en` hoặc `WHISPER_MODEL=small.en`

### Text-to-Speech (TTS)
- Dùng browser SpeechSynthesis API (miễn phí, không gọi backend)
- Nút "🔊 Đọc câu hỏi" trên mỗi câu hỏi AI
- Toggle "Tự động" để tự động đọc câu hỏi mới

### Lưu ý
- Speech metrics chỉ là chỉ số trình bày, **không phải đánh giá tự tin tuyệt đối**
- Audio files được lưu tại `backend/uploads/audio/`
- Yêu cầu browser hỗ trợ MediaRecorder API (Chrome, Firefox, Edge)

## Export Report

### Cách dùng
1. Trên trang `/report/[id]`, **generate report** trước (nếu chưa có)
2. Sau khi report hiển thị, sẽ có nhóm nút **"📥 Tải báo cáo"**:
   - **📄 Tải Markdown** — tải file `.md` có thể đọc trực tiếp
   - **📑 Tải PDF** — tải file `.pdf`
3. File sẽ tự động download với tên `interview_report_session_{id}.md/.pdf`

### API Endpoint
```
GET /interviews/{session_id}/report/export?format=markdown
GET /interviews/{session_id}/report/export?format=pdf
```

### Lưu ý
- Export **không gọi LLM** — chỉ dùng report đã lưu trong database
- Cần **generate report trước** khi export (nếu chưa có report, sẽ trả lỗi 404)
- PDF sử dụng `reportlab` — hỗ trợ tiếng Việt qua font Arial/DejaVu nếu có trên hệ thống

## Chưa làm (Roadmap)

- [x] Voice/Audio input (speech-to-text) ✅
- [x] Text-to-Speech cho câu hỏi ✅
- [x] Export Report as PDF/Markdown ✅
- [ ] Authentication & user accounts
- [ ] Multiple LLM provider switching in UI
- [ ] Deployment (Docker, cloud)
- [ ] Frontend unit tests
- [ ] Dark mode
- [ ] Mobile-optimized responsive
- [ ] Multi-language support
- [ ] Real-time STT (streaming)

## Audio/STT Troubleshooting

## Language Policy

Interview content now follows this default language policy:

```env
INTERVIEW_QUESTION_LANGUAGE=en
CANDIDATE_EXPECTED_LANGUAGE=en
FEEDBACK_LANGUAGE=vi
REPORT_LANGUAGE=vi
STT_LANGUAGE=en
```

- AI interviewer questions are generated in English only.
- Candidates are expected to answer in English, both text and voice.
- Speech-to-text prefers English transcription.
- Per-answer feedback and final reports remain Vietnamese.
- The UI can remain Vietnamese; only interview questions and candidate answers are language-constrained.

### Demo nhanh khong can FFmpeg

Dung mock transcript de demo end-to-end ma khong can cai them cong cu audio:

```env
STT_PROVIDER=mock
WHISPER_MODEL=base.en
STT_LANGUAGE=en
```

Voi cau hinh nay endpoint `POST /interviews/{session_id}/answer-audio` van luu audio, tao transcript mau, tinh speech metrics va chay evaluation.

### Dung Whisper that

Neu dung OpenAI Whisper local hoac faster-whisper:

```env
STT_PROVIDER=whisper
WHISPER_MODEL=base.en
STT_LANGUAGE=en
# hoac
STT_PROVIDER=faster-whisper
WHISPER_MODEL=base.en
STT_LANGUAGE=en
```

Backend se convert audio upload tu browser sang WAV mono 16 kHz truoc khi goi Whisper:

```bash
ffmpeg -y -i input.webm -ac 1 -ar 16000 output.wav
```

May chay backend can co `ffmpeg` trong `PATH`. Kiem tra bang:

```bash
ffmpeg -version
```

Neu Windows bao khong tim thay `ffmpeg`, cai bang:

```powershell
winget install Gyan.FFmpeg
```

Sau khi cai, dong/mo lai terminal hoac VS Code de PATH moi co hieu luc, roi chay lai:

```bash
ffmpeg -version
```

Neu thieu FFmpeg, backend se tra loi ro rang:

```text
FFmpeg is required for audio transcription but was not found. Please install FFmpeg and add it to PATH.
```
