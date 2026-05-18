# E2E Checklist — AI Mock Interviewer

Checklist kiểm tra end-to-end trước khi demo.

## Backend

- [ ] Backend start OK: `uvicorn app.main:app --reload`
- [ ] `pytest -q` pass (54 tests expected)
- [ ] Swagger UI accessible: http://localhost:8000/docs
- [ ] `.env` có `GEMINI_API_KEY` hợp lệ
- [ ] `STT_PROVIDER` env set (mock/whisper/faster-whisper)

## Frontend

- [ ] `npm install` OK
- [ ] `npm run build` pass (no TypeScript errors)
- [ ] `npm run dev` OK
- [ ] http://localhost:3000 accessible
- [ ] `.env.local` có `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

## Home Page `/`

- [ ] Trang load OK
- [ ] Hiển thị workflow steps
- [ ] Backend Status hiển thị "Đang chạy" (xanh)
- [ ] Nút "Bắt đầu Demo" navigate tới `/setup`

## Setup Page `/setup`

- [ ] Upload CV file (.pdf, .docx, hoặc .txt)
- [ ] Upload status chuyển "Hoàn tất"
- [ ] Parse CV — status chuyển "Hoàn tất"
- [ ] Parsed JSON có thể expand/collapse
- [ ] Index CV — status chuyển "Hoàn tất"
- [ ] Upload JD file
- [ ] Parse JD
- [ ] Index JD
- [ ] Card CV/JD hiển thị "✓ Sẵn sàng" khi 3 bước xong
- [ ] Nút "Start Interview" enabled khi cả CV+JD sẵn sàng
- [ ] Start Interview navigate tới `/interview/[id]`
- [ ] Sample data download links hoạt động
- [ ] Reset Demo button xóa state

## Interview Page — Text Mode `/interview/[id]`

- [ ] Câu hỏi đầu tiên hiển thị
- [ ] Tab toggle "Văn bản" / "Giọng nói" hiển thị
- [ ] Textarea nhập câu trả lời (text mode)
- [ ] Submit text answer thành công
- [ ] Evaluation hiển thị sau submit (score bars, feedback)
- [ ] Evaluation có thể expand/collapse chi tiết
- [ ] Next question hiển thị sau submit
- [ ] Submit answer lần 2 thành công
- [ ] Nút "Kết thúc phỏng vấn" hoạt động
- [ ] Sau end: hiển thị "Phỏng vấn đã kết thúc"
- [ ] Nút "Xem báo cáo" navigate tới `/report/[id]`
- [ ] Không cho submit answer rỗng
- [ ] Loading state hiển thị khi AI đang xử lý

## Interview Page — Voice Mode `/interview/[id]`

- [ ] Chuyển sang tab "Giọng nói"
- [ ] Browser xin quyền microphone
- [ ] Bắt đầu ghi âm hoạt động
- [ ] Timer ghi âm chạy đúng
- [ ] Dừng ghi âm hoạt động
- [ ] Audio preview phát lại được
- [ ] Nút "Xóa và ghi lại" hoạt động
- [ ] Submit audio answer thành công
- [ ] Transcript hiển thị (nội dung voice đã nhận diện)
- [ ] Speech metrics hiển thị (thời lượng, số từ, tốc độ nói, từ đệm)
- [ ] Evaluation hiển thị (giống text mode)
- [ ] Next question hiển thị
- [ ] Trình duyệt không hỗ trợ MediaRecorder → UI báo lỗi
- [ ] Từ chối quyền microphone → UI báo lỗi
- [ ] Disclaimer "chỉ hỗ trợ luyện tập" hiển thị

## Interview Page — TTS

- [ ] Nút "Đọc câu hỏi" hoạt động (SpeechSynthesis)
- [ ] Nút "Dừng đọc" khi đang đọc
- [ ] Toggle "Tự động" bật → câu hỏi mới tự động đọc
- [ ] Toggle "Tự động" tắt → không tự động đọc

## Report Page `/report/[id]`

- [ ] Summary card hiển thị (điểm TB, best/weakest criterion)
- [ ] Score bars cho 6 tiêu chí
- [ ] Nút "Generate Report bằng AI" hoạt động
- [ ] Loading text hiển thị khi AI đang tạo report
- [ ] Report hiển thị sau generate
- [ ] Overall score hiển thị
- [ ] Điểm mạnh (strengths) hiển thị
- [ ] Điểm yếu (weaknesses) hiển thị
- [ ] Skill Gaps hiển thị
- [ ] Kế hoạch cải thiện hiển thị
- [ ] Chủ đề ôn tập hiển thị (tags)
- [ ] Lời khuyên hiển thị
- [ ] Nút Regenerate Report hoạt động
- [ ] Refresh page → report vẫn load được
- [ ] Back links hoạt động (Interview, Demo mới)

## Error Handling

- [ ] Upload file không hợp lệ → hiển thị error message
- [ ] Backend offline → hiển thị "Không thể kết nối"
- [ ] Submit empty answer → button disabled
- [ ] API 400/404 → hiển thị error rõ ràng
- [ ] UI không crash khi có lỗi

## Report Export

- [ ] Generate report thành công
- [ ] Nút "📄 Tải Markdown" enabled sau khi có report
- [ ] Tải Markdown thành công
- [ ] File .md mở được và có nội dung báo cáo đầy đủ
- [ ] Nút "📑 Tải PDF" enabled sau khi có report
- [ ] Tải PDF thành công
- [ ] File .pdf mở được
- [ ] Nếu report chưa có, nút export không hiển thị
- [ ] Export không gọi LLM (chỉ dùng report đã lưu)

## Notes

- Sample files: `frontend/public/demo_samples/`
- Backend tests: `cd backend && pytest -q`
- Frontend build: `cd frontend && npm run build`
- STT mock mode: `STT_PROVIDER=mock` (default, no real STT needed for demo)
- STT real mode: `pip install faster-whisper` + `STT_PROVIDER=faster-whisper`
