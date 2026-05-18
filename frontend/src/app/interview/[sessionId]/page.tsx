"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { endInterview, getInterview, submitAnswer, submitAudioAnswer } from "@/lib/api";
import {
  AnimatedPage,
  AudioWave,
  Badge,
  Button,
  Card,
  CriteriaScoreGrid,
  EmptyState,
  ErrorAlert,
  EvaluationPanel,
  LoadingState,
  MetricCard,
  PageContainer,
  SpeechMetricsCard,
  SpeechMetricsGrid,
  StatusBadge,
  TechBackground,
} from "@/components/ui";
import type { Evaluation, SpeechMetrics } from "@/types";

interface Round {
  question: string;
  answer: string;
  evaluation: Evaluation | null;
  speechMetrics: SpeechMetrics | null;
  showDetails: boolean;
}

function speakText(text: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  const voice = window.speechSynthesis
    .getVoices()
    .find((item) => item.lang.toLowerCase().startsWith("en"));
  if (voice) utterance.voice = voice;
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
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

export default function InterviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);

  const [currentQuestion, setCurrentQuestion] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [rounds, setRounds] = useState<Round[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [error, setError] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [roundNumber, setRoundNumber] = useState(1);

  const [answerMode, setAnswerMode] = useState<"text" | "voice">("text");
  const [recording, setRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [micError, setMicError] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [autoRead, setAutoRead] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const latestEvaluation = [...rounds].reverse().find((round) => round.evaluation)?.evaluation ?? null;
  const latestSpeechMetrics = [...rounds].reverse().find((round) => round.speechMetrics)?.speechMetrics ?? null;

  useEffect(() => {
    async function loadSession() {
      try {
        const history = await getInterview(sessionId);
        if (history.status === "completed") setSessionEnded(true);
        const reconstructedRounds: Round[] = [];
        let lastQuestion = "";
        for (const message of history.messages) {
          if (message.role === "interviewer") lastQuestion = message.content;
          if (message.role === "candidate" && lastQuestion) {
            reconstructedRounds.push({
              question: lastQuestion,
              answer: message.content,
              evaluation: null,
              speechMetrics: null,
              showDetails: false,
            });
            lastQuestion = "";
          }
        }
        setRounds(reconstructedRounds);
        setRoundNumber(reconstructedRounds.length + 1);
        const lastMessage = history.messages[history.messages.length - 1];
        if (lastMessage?.role === "interviewer") setCurrentQuestion(lastMessage.content);
      } catch {
        setError("Không thể tải session. Vui lòng kiểm tra session ID.");
      } finally {
        setLoadingHistory(false);
      }
    }
    if (sessionId) loadSession();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [rounds, currentQuestion]);

  useEffect(() => {
    if (autoRead && currentQuestion && !sessionEnded) speakText(currentQuestion);
  }, [autoRead, currentQuestion, sessionEnded]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    const interval = setInterval(() => setIsSpeaking(window.speechSynthesis.speaking), 200);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    return () => {
      stopSpeaking();
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const startRecording = useCallback(async () => {
    setMicError("");
    if (audioUrl) URL.revokeObjectURL(audioUrl);
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
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((track) => track.stop());
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      };

      recorder.start();
      setRecording(true);
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setRecordingDuration(Math.round((Date.now() - start) / 1000));
      }, 500);
    } catch {
      setMicError("Không thể truy cập microphone. Hãy cấp quyền và thử lại.");
    }
  }, [audioUrl]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
  }, []);

  const handleSubmitText = async () => {
    if (!answerText.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await submitAnswer(sessionId, answerText.trim());
      setRounds((previous) => [
        ...previous,
        {
          question: currentQuestion,
          answer: response.candidate_answer,
          evaluation: response.evaluation,
          speechMetrics: null,
          showDetails: true,
        },
      ]);
      setCurrentQuestion(response.next_question);
      setAnswerText("");
      setRoundNumber((value) => value + 1);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Gửi câu trả lời thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitAudio = async () => {
    if (!audioBlob) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await submitAudioAnswer(sessionId, audioBlob);
      setRounds((previous) => [
        ...previous,
        {
          question: currentQuestion,
          answer: response.transcript,
          evaluation: response.evaluation,
          speechMetrics: response.speech_metrics,
          showDetails: true,
        },
      ]);
      setCurrentQuestion(response.next_question);
      setAudioBlob(null);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
      setRecordingDuration(0);
      setRoundNumber((value) => value + 1);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Gửi câu trả lời bằng giọng nói thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEnd = async () => {
    if (!confirm("Bạn có chắc muốn kết thúc phỏng vấn?")) return;
    setEnding(true);
    setError("");
    try {
      await endInterview(sessionId);
      setSessionEnded(true);
      stopSpeaking();
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Kết thúc phỏng vấn thất bại.");
    } finally {
      setEnding(false);
    }
  };

  const toggleDetails = (index: number) => {
    setRounds((previous) => previous.map((round, itemIndex) => (itemIndex === index ? { ...round, showDetails: !round.showDetails } : round)));
  };

  if (loadingHistory) {
    return <LoadingState title="Đang tải phiên phỏng vấn..." subtitle="Preparing your virtual interview room." />;
  }

  return (
    <PageContainer className="space-y-6 overflow-hidden">
      <TechBackground />
      <AnimatedPage className="relative space-y-6">
      <div className="sticky top-[72px] z-40 -mx-4 border-b border-slate-800 bg-slate-950/85 px-4 py-4 backdrop-blur-xl sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-black tracking-tight text-slate-50">Technical Interview Room</h1>
              <StatusBadge status={sessionEnded ? "completed" : "active"} />
            </div>
            <p className="mt-1 text-sm text-slate-400">
              Session #{sessionId} · {sessionEnded ? "Đã kết thúc" : `Round ${roundNumber}`}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {sessionEnded && (
              <Button type="button" onClick={() => router.push(`/report/${sessionId}`)}>
                View Report
              </Button>
            )}
            {!sessionEnded && rounds.length > 0 && (
              <Button type="button" variant="danger" loading={ending} onClick={handleEnd}>
                End Interview
              </Button>
            )}
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError("")} />}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <main className="min-w-0 space-y-6">
          {rounds.length === 0 && !sessionEnded && (
            <EmptyState
              title="First question is ready"
              description="Answer in English. Feedback and improvement suggestions will be shown in Vietnamese after submission."
            />
          )}

          {rounds.map((round, index) => (
            <section key={index} className="space-y-4">
              <QuestionCard question={round.question} round={index + 1} compact />
              <Card className="ml-0 border-emerald-500/30 bg-slate-900/80 sm:ml-8">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge tone="emerald">Candidate · {round.speechMetrics ? "Voice" : "Text"}</Badge>
                  <span className="text-xs text-slate-400">Transcript / answer in English</span>
                </div>
                <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-200">{round.answer}</p>
              </Card>
              {round.speechMetrics && <div className="sm:ml-8"><SpeechMetricsCard metrics={round.speechMetrics} /></div>}
              {round.evaluation && (
                <div className="sm:ml-8">
                  <EvaluationPanel
                    evaluation={round.evaluation}
                    expanded={round.showDetails}
                    onToggle={() => toggleDetails(index)}
                  />
                </div>
              )}
            </section>
          ))}

          {!sessionEnded && currentQuestion && (
            <section className="space-y-4">
              <QuestionCard
                question={currentQuestion}
                round={roundNumber}
                actions={
                  <>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => (isSpeaking ? stopSpeaking() : speakText(currentQuestion))}
                      className="min-h-9 px-3"
                    >
                      {isSpeaking ? "Stop TTS" : "Read question"}
                    </Button>
                    <label className="inline-flex min-h-9 items-center gap-2 rounded-xl bg-slate-800 px-3 text-xs font-semibold text-slate-300 ring-1 ring-slate-700">
                      <input
                        type="checkbox"
                        checked={autoRead}
                        onChange={(event) => setAutoRead(event.target.checked)}
                        className="h-3.5 w-3.5 accent-blue-600"
                      />
                      Auto-read
                    </label>
                  </>
                }
              />

              <Card className="sm:ml-8">
                <div className="mb-5 grid grid-cols-2 rounded-2xl bg-slate-950/70 p-1 ring-1 ring-slate-800">
                  <button
                    type="button"
                    className={`rounded-xl px-3 py-2 text-sm font-bold transition ${answerMode === "text" ? "bg-slate-800 text-cyan-200 shadow-sm" : "text-slate-500 hover:text-slate-100"}`}
                    onClick={() => setAnswerMode("text")}
                  >
                    Text answer
                  </button>
                  <button
                    type="button"
                    className={`rounded-xl px-3 py-2 text-sm font-bold transition ${answerMode === "voice" ? "bg-slate-800 text-violet-200 shadow-sm" : "text-slate-500 hover:text-slate-100"}`}
                    onClick={() => setAnswerMode("voice")}
                  >
                    Voice answer
                  </button>
                </div>

                {answerMode === "text" ? (
                  <div className="space-y-3">
                    <label htmlFor="answerText" className="text-sm font-bold text-slate-100">
                      Candidate answer
                    </label>
                    <textarea
                      id="answerText"
                      value={answerText}
                      onChange={(event) => setAnswerText(event.target.value)}
                      placeholder="Type your answer in English..."
                      rows={7}
                      disabled={submitting}
                      className="w-full resize-y rounded-2xl border border-slate-700 bg-slate-950 p-4 text-sm leading-7 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-4 focus:ring-cyan-400/10 disabled:opacity-50"
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && event.ctrlKey && answerText.trim()) handleSubmitText();
                      }}
                    />
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-xs leading-5 text-slate-500">
                        Vui lòng trả lời bằng tiếng Anh. Nhận xét sẽ hiển thị bằng tiếng Việt.
                      </p>
                      <Button type="button" loading={submitting} disabled={!answerText.trim()} onClick={handleSubmitText}>
                        {submitting ? "Đang đánh giá..." : "Submit Answer"}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <AudioRecorderPanel
                    recording={recording}
                    recordingDuration={recordingDuration}
                    audioBlob={audioBlob}
                    audioUrl={audioUrl}
                    micError={micError}
                    submitting={submitting}
                    onStart={startRecording}
                    onStop={stopRecording}
                    onClear={() => {
                      if (audioUrl) URL.revokeObjectURL(audioUrl);
                      setAudioBlob(null);
                      setAudioUrl(null);
                      setRecordingDuration(0);
                    }}
                    onSubmit={handleSubmitAudio}
                    onDismissError={() => setMicError("")}
                  />
                )}
              </Card>
            </section>
          )}

          {sessionEnded && (
            <Card className="border-emerald-500/30 bg-emerald-500/10 text-center">
              <h2 className="text-xl font-bold text-emerald-950">Phỏng vấn đã kết thúc</h2>
              <p className="mt-2 text-sm text-slate-300">Bạn đã hoàn thành {rounds.length} câu hỏi.</p>
              <div className="mt-5 flex flex-col justify-center gap-3 sm:flex-row">
                <Button type="button" onClick={() => router.push(`/report/${sessionId}`)}>
                  View Report
                </Button>
                <Button type="button" variant="secondary" onClick={() => router.push("/setup")}>
                  New Interview
                </Button>
              </div>
            </Card>
          )}
          <div ref={bottomRef} />
        </main>

        <aside className="min-w-0 space-y-4 xl:sticky xl:top-36 xl:self-start">
          <Card>
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Interview status</h2>
            <div className="mt-4 grid gap-3">
              <MetricCard label="Session" value={`#${sessionId}`} tone="slate" />
              <MetricCard label="Current round" value={sessionEnded ? rounds.length : roundNumber} tone="blue" />
              <MetricCard label="Answered" value={rounds.length} tone="emerald" />
            </div>
          </Card>

          {latestSpeechMetrics ? (
            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-50">Latest speech metrics</h2>
                <Badge tone="violet">Voice</Badge>
              </div>
              <SpeechMetricsGrid metrics={latestSpeechMetrics} />
            </Card>
          ) : (
            <Card>
              <h2 className="text-sm font-bold text-slate-50">Speech metrics</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">Voice metrics will appear after an audio answer.</p>
            </Card>
          )}

          {latestEvaluation ? (
            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-50">Latest evaluation</h2>
                <Badge tone="indigo">{latestEvaluation.score_overall.toFixed(1)}/10</Badge>
              </div>
              <CriteriaScoreGrid scores={latestEvaluation.scores} />
            </Card>
          ) : (
            <Card>
              <h2 className="text-sm font-bold text-slate-50">Evaluation panel</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">Vietnamese feedback will appear after the first answer.</p>
            </Card>
          )}

          <Card className="bg-slate-950 text-white">
            <h2 className="text-sm font-bold">Interview tips</h2>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
              <li>• Answer in English and structure with context, action, result.</li>
              <li>• Mention trade-offs and technical details when relevant.</li>
              <li>• Keep examples aligned with the uploaded JD.</li>
            </ul>
          </Card>
        </aside>
      </div>
      </AnimatedPage>
    </PageContainer>
  );
}

function QuestionCard({
  question,
  round,
  actions,
  compact = false,
}: {
  question: string;
  round: number;
  actions?: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <Card className="animate-slide-up-fade relative overflow-hidden border-cyan-500/30 bg-slate-900/85">
      <div className="tech-grid absolute inset-0 opacity-30" aria-hidden="true" />
      <div className="relative">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-500 text-sm font-black text-slate-950 shadow-lg shadow-cyan-500/20">
            AI
          </div>
          <div>
            <Badge tone="blue">AI Interviewer · Round {round}</Badge>
            {!compact && <p className="mt-1 text-xs text-slate-500">Question language: English</p>}
          </div>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      <p className="mt-4 whitespace-pre-wrap break-words text-base font-semibold leading-8 text-slate-50">{question}</p>
      </div>
    </Card>
  );
}

function AudioRecorderPanel({
  recording,
  recordingDuration,
  audioBlob,
  audioUrl,
  micError,
  submitting,
  onStart,
  onStop,
  onClear,
  onSubmit,
  onDismissError,
}: {
  recording: boolean;
  recordingDuration: number;
  audioBlob: Blob | null;
  audioUrl: string | null;
  micError: string;
  submitting: boolean;
  onStart: () => void;
  onStop: () => void;
  onClear: () => void;
  onSubmit: () => void;
  onDismissError: () => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-bold text-slate-100">Audio recorder</p>
        <p className="mt-1 text-sm leading-6 text-slate-400">
          Record an English answer. The backend will transcribe, evaluate, and return the next English question.
        </p>
      </div>

      {micError && <ErrorAlert message={micError} onDismiss={onDismissError} />}
      {(recording || submitting) && <AudioWave active={recording || submitting} />}
      {submitting && <Badge tone="blue">Đang chuyển giọng nói thành văn bản và đánh giá...</Badge>}

      <div className="flex flex-wrap items-center gap-3">
        {!recording && !audioBlob && (
          <Button type="button" variant="danger" disabled={submitting} onClick={onStart}>
            <span className="h-2.5 w-2.5 rounded-full bg-white" />
            Start Recording
          </Button>
        )}
        {recording && (
          <Button type="button" variant="danger" onClick={onStop}>
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-white" />
            Stop Recording · {recordingDuration}s
          </Button>
        )}
        {audioBlob && !recording && (
          <Button type="button" variant="ghost" onClick={onClear}>
            Clear and record again
          </Button>
        )}
      </div>

      {recording && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm font-semibold text-rose-100">
          <span className="mr-2 inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-red-600" />
          Recording in progress · {recordingDuration}s
        </div>
      )}

      {audioUrl && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Preview audio</p>
          <audio controls src={audioUrl} className="w-full" />
        </div>
      )}

      {audioBlob && !recording && (
        <div className="flex justify-end">
          <Button type="button" loading={submitting} onClick={onSubmit}>
            {submitting ? "Processing audio..." : "Submit Audio Answer"}
          </Button>
        </div>
      )}
    </div>
  );
}
