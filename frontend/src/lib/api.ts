// -----------------------------------------------------------------------
// API client for AI Mock Interviewer backend
// -----------------------------------------------------------------------

import type {
  DocumentItem,
  DocumentUploadResponse,
  ParsedDocument,
  IndexDocumentResponse,
  StartInterviewResponse,
  SubmitAnswerResponse,
  SubmitAudioAnswerResponse,
  TranscribeAudioResponse,
  InterviewHistory,
  EndInterviewResponse,
  InterviewReport,
  InterviewSummary,
  SessionEvaluations,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/** Expose the configured base URL for status display */
export function getBaseUrl(): string {
  return BASE_URL;
}

// -----------------------------------------------------------------------
// Generic fetch helper — handles HTTP errors + network errors
// -----------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let res: Response;

  try {
    res = await fetch(url, options);
  } catch {
    throw new Error(
      "Không thể kết nối tới backend. Hãy kiểm tra backend đang chạy tại " + BASE_URL
    );
  }

  if (!res.ok) {
    let message = `Lỗi HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) message = String(body.detail);
      else if (body.message) message = String(body.message);
    } catch {
      /* ignore parse errors */
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

// -----------------------------------------------------------------------
// Health check
// -----------------------------------------------------------------------

export async function checkBackendHealth(): Promise<boolean> {
  try {
    await apiFetch<{ message: string }>("/");
    return true;
  } catch {
    return false;
  }
}

// -----------------------------------------------------------------------
// Documents
// -----------------------------------------------------------------------

export async function uploadDocument(
  file: File,
  documentType: "CV" | "JD"
): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("document_type", documentType);

  return apiFetch<DocumentUploadResponse>("/documents/upload", {
    method: "POST",
    body: form,
  });
}

export async function getDocuments(): Promise<DocumentItem[]> {
  return apiFetch<DocumentItem[]>("/documents");
}

export async function parseDocument(
  documentId: number
): Promise<ParsedDocument> {
  return apiFetch<ParsedDocument>(`/documents/${documentId}/parse`, {
    method: "POST",
  });
}

// -----------------------------------------------------------------------
// RAG
// -----------------------------------------------------------------------

export async function indexDocument(
  documentId: number
): Promise<IndexDocumentResponse> {
  return apiFetch<IndexDocumentResponse>(`/rag/index/${documentId}`, {
    method: "POST",
  });
}

// -----------------------------------------------------------------------
// Interviews
// -----------------------------------------------------------------------

export async function startInterview(
  cvDocumentId: number,
  jdDocumentId: number,
  interviewType: string = "technical",
  targetLanguage: string = "vi"
): Promise<StartInterviewResponse> {
  return apiFetch<StartInterviewResponse>("/interviews/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cv_document_id: cvDocumentId,
      jd_document_id: jdDocumentId,
      interview_type: interviewType,
      target_language: targetLanguage,
    }),
  });
}

export async function submitAnswer(
  sessionId: number,
  answer: string
): Promise<SubmitAnswerResponse> {
  return apiFetch<SubmitAnswerResponse>(
    `/interviews/${sessionId}/answer`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    }
  );
}

export async function getInterview(
  sessionId: number
): Promise<InterviewHistory> {
  return apiFetch<InterviewHistory>(`/interviews/${sessionId}`);
}

export async function getEvaluations(
  sessionId: number
): Promise<SessionEvaluations> {
  return apiFetch<SessionEvaluations>(`/interviews/${sessionId}/evaluations`);
}

export async function endInterview(
  sessionId: number
): Promise<EndInterviewResponse> {
  return apiFetch<EndInterviewResponse>(
    `/interviews/${sessionId}/end`,
    { method: "POST" }
  );
}

// -----------------------------------------------------------------------
// Reports
// -----------------------------------------------------------------------

export async function generateReport(
  sessionId: number
): Promise<InterviewReport> {
  return apiFetch<InterviewReport>(
    `/interviews/${sessionId}/report`,
    { method: "POST" }
  );
}

export async function getReport(
  sessionId: number
): Promise<InterviewReport> {
  return apiFetch<InterviewReport>(`/interviews/${sessionId}/report`);
}

export async function getSummary(
  sessionId: number
): Promise<InterviewSummary> {
  return apiFetch<InterviewSummary>(`/interviews/${sessionId}/summary`);
}

// -----------------------------------------------------------------------
// Audio Answers
// -----------------------------------------------------------------------

export async function submitAudioAnswer(
  sessionId: number,
  audioBlob: Blob
): Promise<SubmitAudioAnswerResponse> {
  const form = new FormData();
  const filename = audioBlob.type.includes("ogg") ? "answer.ogg" : "answer.webm";
  form.append("audio_file", audioBlob, filename);

  return apiFetch<SubmitAudioAnswerResponse>(
    `/interviews/${sessionId}/answer-audio`,
    {
      method: "POST",
      body: form,
    }
  );
}

/**
 * Step 1 of the 2-step voice flow:
 * Upload audio → transcribe → return transcript + speech_metrics.
 * Does NOT save a candidate answer, does NOT evaluate, does NOT generate next question.
 * The user reviews/edits the transcript, then calls submitAnswer() to confirm.
 */
export async function transcribeAudio(
  sessionId: number,
  audioBlob: Blob
): Promise<TranscribeAudioResponse> {
  const form = new FormData();
  const filename = audioBlob.type.includes("ogg") ? "answer.ogg" : "answer.webm";
  form.append("audio_file", audioBlob, filename);

  return apiFetch<TranscribeAudioResponse>(
    `/interviews/${sessionId}/transcribe-audio`,
    {
      method: "POST",
      body: form,
    }
  );
}

// -----------------------------------------------------------------------
// Report Export
// -----------------------------------------------------------------------

export async function exportReport(
  sessionId: number,
  format: "markdown" | "pdf"
): Promise<Blob> {
  const url = `${BASE_URL}/interviews/${sessionId}/report/export?format=${format}`;
  let res: Response;

  try {
    res = await fetch(url);
  } catch {
    throw new Error(
      "Không thể kết nối tới backend. Hãy kiểm tra backend đang chạy tại " + BASE_URL
    );
  }

  if (!res.ok) {
    let message = `Lỗi HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) message = String(body.detail);
      else if (body.message) message = String(body.message);
    } catch {
      /* ignore parse errors */
    }
    throw new Error(message);
  }

  return res.blob();
}

/**
 * Trigger a file download in the browser from a Blob.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
