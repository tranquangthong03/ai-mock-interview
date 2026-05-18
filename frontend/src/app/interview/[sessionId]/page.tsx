"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  submitAnswer,
  submitAudioAnswer,
  endInterview,
  getInterview,
} from "@/lib/api";
import {
  LoadingButton,
  ErrorAlert,
  Card,
  ScoreBar,
  JsonPreview,
  SpeechMetricsCard,
} from "@/components/ui";
import type { Evaluation, SpeechMetrics } from "@/types";

interface Round {
  question: string;
  answer: string;
  evaluation: Evaluation | null;
  speechMetrics: SpeechMetrics | null;
  showDetails: boolean;
}

// ---------------------------------------------------------------------------
// TTS helper
// ---------------------------------------------------------------------------

function speakText(text: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  const voices = window.speechSynthesis.getVoices();
  const englishVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("en"));
  if (englishVoice) u.voice = englishVoice;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

function stopSpeaking() {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function getSupportedAudioMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function InterviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);

  // --- State ---
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [rounds, setRounds] = useState<Round[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [error, setError] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [roundNumber, setRoundNumber] = useState(1);

  // Voice mode
  const [answerMode, setAnswerMode] = useState<"text" | "voice">("text");
  const [recording, setRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [micError, setMicError] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // TTS
  const [autoRead, setAutoRead] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  // --- Load session history ---
  useEffect(() => {
    async function loadSession() {
      try {
        const history = await getInterview(sessionId);
        if (history.status === "completed") setSessionEnded(true);
        const msgs = history.messages;
        const reconstructedRounds: Round[] = [];
        let lastQuestion = "";
        for (const msg of msgs) {
          if (msg.role === "interviewer") lastQuestion = msg.content;
          else if (msg.role === "candidate" && lastQuestion) {
            reconstructedRounds.push({
              question: lastQuestion,
              answer: msg.content,
              evaluation: null,
              speechMetrics: null,
              showDetails: false,
            });
            lastQuestion = "";
          }
        }
        setRounds(reconstructedRounds);
        setRoundNumber(reconstructedRounds.length + 1);
        const lastMsg = msgs[msgs.length - 1];
        if (lastMsg?.role === "interviewer") setCurrentQuestion(lastMsg.content);
      } catch {
        setError("Không thể tải session. Vui lòng kiểm tra session ID.");
      } finally {
        setLoadingHistory(false);
      }
    }
    if (sessionId) loadSession();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rounds, currentQuestion]);

  // Auto-read new questions
  useEffect(() => {
    if (autoRead && currentQuestion && !sessionEnded) {
      speakText(currentQuestion);
    }
  }, [currentQuestion, autoRead, sessionEnded]);

  // Track speaking state
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    const interval = setInterval(() => {
      setIsSpeaking(window.speechSynthesis.speaking);
    }, 200);
    return () => clearInterval(interval);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // --- Audio Recording ---
  const startRecording = useCallback(async () => {
    setMicError("");
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingDuration(0);
    chunksRef.current = [];

    if (!navigator.mediaDevices?.getUserMedia) {
      setMicError("Trình duyệt không hỗ trợ ghi âm. Hãy dùng Chrome hoặc Firefox.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedAudioMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      };

      recorder.start();
      setRecording(true);

      // Timer
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setRecordingDuration(Math.round((Date.now() - start) / 1000));
      }, 500);
    } catch {
      setMicError("Không thể truy cập microphone. Hãy cấp quyền và thử lại.");
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  // --- Submit text answer ---
  const handleSubmitText = async () => {
    if (!answerText.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await submitAnswer(sessionId, answerText.trim());
      setRounds((prev) => [
        ...prev,
        {
          question: currentQuestion,
          answer: res.candidate_answer,
          evaluation: res.evaluation,
          speechMetrics: null,
          showDetails: true,
        },
      ]);
      setCurrentQuestion(res.next_question);
      setAnswerText("");
      setRoundNumber((n) => n + 1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Gửi câu trả lời thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  // --- Submit audio answer ---
  const handleSubmitAudio = async () => {
    if (!audioBlob) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await submitAudioAnswer(sessionId, audioBlob);
      setRounds((prev) => [
        ...prev,
        {
          question: currentQuestion,
          answer: res.transcript,
          evaluation: res.evaluation,
          speechMetrics: res.speech_metrics,
          showDetails: true,
        },
      ]);
      setCurrentQuestion(res.next_question);
      setAudioBlob(null);
      setAudioUrl(null);
      setRecordingDuration(0);
      setRoundNumber((n) => n + 1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Gửi câu trả lời bằng giọng nói thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  // --- End interview ---
  const handleEnd = async () => {
    if (!confirm("Bạn có chắc muốn kết thúc phỏng vấn?")) return;
    setEnding(true);
    setError("");
    try {
      await endInterview(sessionId);
      setSessionEnded(true);
      stopSpeaking();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Kết thúc phỏng vấn thất bại.");
    } finally {
      setEnding(false);
    }
  };

  const toggleDetails = (idx: number) => {
    setRounds((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, showDetails: !r.showDetails } : r))
    );
  };

  // --- Loading ---
  if (loadingHistory) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--primary)] border-t-transparent rounded-full" />
        <p className="text-sm text-[var(--muted)]">Đang tải phiên phỏng vấn...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">🎤 Phỏng vấn</h1>
          <p className="text-sm text-[var(--muted)]">
            Session #{sessionId} · {sessionEnded ? "Đã kết thúc" : `Vòng ${roundNumber}`}
          </p>
        </div>
        <div className="flex gap-2">
          {sessionEnded && (
            <LoadingButton variant="primary" onClick={() => router.push(`/report/${sessionId}`)}>
              📊 Xem báo cáo
            </LoadingButton>
          )}
          {!sessionEnded && rounds.length > 0 && (
            <LoadingButton variant="danger" loading={ending} onClick={handleEnd}>
              ⏹ Kết thúc phỏng vấn
            </LoadingButton>
          )}
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError("")} />}

      {/* Conversation history */}
      {rounds.map((r, i) => (
        <div key={i} className="space-y-3">
          {/* Interviewer question */}
          <Card className="border-l-4 border-l-[var(--primary)]">
            <div className="flex items-center gap-2 text-sm text-[var(--muted)] mb-2">
              <span className="font-medium text-[var(--primary)]">🤖 AI Interviewer</span>
              <span>· Vòng {i + 1}</span>
            </div>
            <p className="whitespace-pre-wrap leading-relaxed">{r.question}</p>
          </Card>

          {/* Candidate answer */}
          <Card className="border-l-4 border-l-emerald-500 ml-4 sm:ml-8">
            <div className="text-sm text-[var(--muted)] mb-2 font-medium text-emerald-600">
              👤 Ứng viên {r.speechMetrics ? "(🎙️ voice)" : "(⌨️ text)"}
            </div>
            <p className="whitespace-pre-wrap leading-relaxed">{r.answer}</p>
          </Card>

          {/* Speech Metrics */}
          {r.speechMetrics && (
            <div className="ml-4 sm:ml-8">
              <SpeechMetricsCard metrics={r.speechMetrics} />
            </div>
          )}

          {/* Evaluation */}
          {r.evaluation && (
            <Card className="ml-4 sm:ml-8 bg-slate-50/50 border-slate-200">
              <div className="flex items-center justify-between cursor-pointer" onClick={() => toggleDetails(i)}>
                <h4 className="font-semibold text-sm text-slate-800">
                  📊 Đánh giá · Điểm tổng: {r.evaluation.score_overall.toFixed(1)}/10
                </h4>
                <span className="text-xs text-[var(--muted)]">
                  {r.showDetails ? "▼ Thu gọn" : "▶ Xem chi tiết"}
                </span>
              </div>
              <p className="text-sm text-gray-700 mt-2 italic">💬 {r.evaluation.short_feedback}</p>

              {r.showDetails && (
                <div className="mt-4 space-y-4">
                  <div className="space-y-1.5">
                    <ScoreBar label="Relevance" score={r.evaluation.scores.relevance} />
                    <ScoreBar label="Clarity" score={r.evaluation.scores.clarity} />
                    <ScoreBar label="Specificity" score={r.evaluation.scores.specificity} />
                    <ScoreBar label="Technical Accuracy" score={r.evaluation.scores.technical_accuracy} />
                    <ScoreBar label="JD Alignment" score={r.evaluation.scores.jd_alignment} />
                    <ScoreBar label="Communication" score={r.evaluation.scores.communication} />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {r.evaluation.strengths?.length > 0 && (
                      <div className="bg-emerald-50 rounded-lg p-3">
                        <span className="text-xs font-semibold text-emerald-700 block mb-1">✅ Điểm mạnh</span>
                        <ul className="text-xs text-gray-700 space-y-0.5">
                          {r.evaluation.strengths.map((s, j) => <li key={j}>• {s}</li>)}
                        </ul>
                      </div>
                    )}
                    {r.evaluation.weaknesses?.length > 0 && (
                      <div className="bg-amber-50 rounded-lg p-3">
                        <span className="text-xs font-semibold text-amber-700 block mb-1">⚠️ Cần cải thiện</span>
                        <ul className="text-xs text-gray-700 space-y-0.5">
                          {r.evaluation.weaknesses.map((w, j) => <li key={j}>• {w}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                  {r.evaluation.suggestions?.length > 0 && (
                    <div className="bg-blue-50 rounded-lg p-3">
                      <span className="text-xs font-semibold text-blue-700 block mb-1">💡 Gợi ý</span>
                      <ul className="text-xs text-gray-700 space-y-0.5">
                        {r.evaluation.suggestions.map((s, j) => <li key={j}>• {s}</li>)}
                      </ul>
                    </div>
                  )}
                  {r.evaluation.improved_answer_suggestion && (
                    <div className="bg-indigo-50 rounded-lg p-3">
                      <span className="text-xs font-semibold text-indigo-700 block mb-1">📝 Câu trả lời mẫu</span>
                      <p className="text-xs text-gray-700 whitespace-pre-wrap">{r.evaluation.improved_answer_suggestion}</p>
                    </div>
                  )}
                  <details className="text-xs">
                    <summary className="text-[var(--muted)] cursor-pointer hover:text-gray-600">🔧 Xem JSON thô</summary>
                    <JsonPreview data={r.evaluation} />
                  </details>
                </div>
              )}
            </Card>
          )}
        </div>
      ))}

      {/* Current question + answer input */}
      {!sessionEnded && currentQuestion && (
        <div className="space-y-3">
          {/* Question card with TTS */}
          <Card className="border-l-4 border-l-[var(--primary)]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <span className="font-medium text-[var(--primary)]">🤖 AI Interviewer</span>
                <span>· Vòng {roundNumber}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => isSpeaking ? stopSpeaking() : speakText(currentQuestion)}
                  className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
                >
                  {isSpeaking ? "⏹ Dừng đọc" : "🔊 Đọc câu hỏi"}
                </button>
                <label className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRead}
                    onChange={(e) => setAutoRead(e.target.checked)}
                    className="w-3 h-3"
                  />
                  Tự động
                </label>
              </div>
            </div>
            <p className="whitespace-pre-wrap leading-relaxed">{currentQuestion}</p>
          </Card>

          {/* Answer mode toggle */}
          <Card className="ml-4 sm:ml-8">
            <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1">
              <button
                className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-all cursor-pointer ${
                  answerMode === "text"
                    ? "bg-white shadow text-[var(--primary)]"
                    : "text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setAnswerMode("text")}
              >
                ⌨️ Trả lời bằng văn bản
              </button>
              <button
                className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-all cursor-pointer ${
                  answerMode === "voice"
                    ? "bg-white shadow text-violet-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setAnswerMode("voice")}
              >
                🎙️ Trả lời bằng giọng nói
              </button>
            </div>

            {/* Text mode */}
            {answerMode === "text" && (
              <>
                <textarea
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your answer in English..."
                  rows={5}
                  disabled={submitting}
                  className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent resize-y disabled:opacity-50"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.ctrlKey && answerText.trim()) handleSubmitText();
                  }}
                />
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-[var(--muted)]">Vui lòng trả lời bằng tiếng Anh. Ctrl+Enter để gửi nhanh</span>
                  <LoadingButton loading={submitting} disabled={!answerText.trim()} onClick={handleSubmitText}>
                    {submitting ? "AI đang đánh giá..." : "Gửi câu trả lời"}
                  </LoadingButton>
                </div>
              </>
            )}

            {/* Voice mode */}
            {answerMode === "voice" && (
              <div className="space-y-4">
                {micError && <ErrorAlert message={micError} onDismiss={() => setMicError("")} />}

                {/* Recording controls */}
                <div className="flex items-center gap-3">
                  {!recording && !audioBlob && (
                    <button
                      onClick={startRecording}
                      disabled={submitting}
                      className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      <span className="w-3 h-3 rounded-full bg-white" />
                      Bắt đầu ghi âm
                    </button>
                  )}

                  {recording && (
                    <button
                      onClick={stopRecording}
                      className="flex items-center gap-2 px-4 py-2 bg-gray-800 text-white rounded-lg font-medium hover:bg-gray-900 transition-colors cursor-pointer"
                    >
                      <span className="w-3 h-3 rounded-sm bg-red-500 animate-pulse" />
                      Dừng ghi âm · {recordingDuration}s
                    </button>
                  )}

                  {audioBlob && !recording && (
                    <button
                      onClick={() => {
                        setAudioBlob(null);
                        setAudioUrl(null);
                        setRecordingDuration(0);
                      }}
                      className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      🗑️ Xóa và ghi lại
                    </button>
                  )}
                </div>

                {/* Audio preview */}
                {audioUrl && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-2">🔊 Nghe lại:</p>
                    <audio controls src={audioUrl} className="w-full h-10" />
                  </div>
                )}

                {/* Submit audio */}
                {audioBlob && !recording && (
                  <div className="flex justify-end">
                    <LoadingButton loading={submitting} onClick={handleSubmitAudio}>
                      {submitting ? "AI đang xử lý audio..." : "🎙️ Gửi câu trả lời bằng giọng nói"}
                    </LoadingButton>
                  </div>
                )}

                {!recording && !audioBlob && (
                  <p className="text-xs text-[var(--muted)]">
                    Nhấn nút để ghi âm câu trả lời bằng tiếng Anh. Audio sẽ được chuyển thành transcript và đánh giá tự động.
                  </p>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Session ended */}
      {sessionEnded && (
        <Card className="text-center bg-emerald-50/50 border-emerald-200">
          <h3 className="font-semibold text-lg text-emerald-800 mb-2">✅ Phỏng vấn đã kết thúc</h3>
          <p className="text-sm text-[var(--muted)] mb-4">Bạn đã hoàn thành {rounds.length} câu hỏi.</p>
          <div className="flex items-center justify-center gap-3">
            <LoadingButton variant="primary" onClick={() => router.push(`/report/${sessionId}`)}>
              📊 Xem báo cáo →
            </LoadingButton>
            <LoadingButton variant="secondary" onClick={() => router.push("/setup")}>
              🔄 Phỏng vấn mới
            </LoadingButton>
          </div>
        </Card>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
