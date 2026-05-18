"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  uploadDocument,
  parseDocument,
  indexDocument,
  startInterview,
} from "@/lib/api";
import {
  setCvDocumentId,
  setJdDocumentId,
  setSessionId,
  clearAll,
} from "@/lib/local-storage";
import {
  LoadingButton,
  ErrorAlert,
  SuccessAlert,
  StepStatusBadge,
  Card,
  JsonPreview,
} from "@/components/ui";
import type { ParsedDocument } from "@/types";

type StepStatus = "pending" | "loading" | "success" | "error";

interface DocState {
  file: File | null;
  docId: number | null;
  filename: string;
  textPreview: string;
  uploadStatus: StepStatus;
  parseStatus: StepStatus;
  indexStatus: StepStatus;
  parsedData: ParsedDocument | null;
  chunksIndexed: number;
  error: string;
  showJson: boolean;
}

const initialDocState: DocState = {
  file: null,
  docId: null,
  filename: "",
  textPreview: "",
  uploadStatus: "pending",
  parseStatus: "pending",
  indexStatus: "pending",
  parsedData: null,
  chunksIndexed: 0,
  error: "",
  showJson: false,
};

const ALLOWED = [".pdf", ".docx", ".txt"];

export default function SetupPage() {
  const router = useRouter();
  const [cv, setCv] = useState<DocState>({ ...initialDocState });
  const [jd, setJd] = useState<DocState>({ ...initialDocState });
  const [interviewLoading, setInterviewLoading] = useState(false);
  const [interviewError, setInterviewError] = useState("");

  // ---------------------------------------------------------------
  // Upload → Parse → Index pipeline
  // ---------------------------------------------------------------

  const handleUpload = useCallback(
    async (
      type: "CV" | "JD",
      state: DocState,
      setState: React.Dispatch<React.SetStateAction<DocState>>
    ) => {
      if (!state.file) return;
      setState((s) => ({ ...s, uploadStatus: "loading", error: "" }));
      try {
        const res = await uploadDocument(state.file, type);
        setState((s) => ({
          ...s,
          uploadStatus: "success",
          docId: res.id,
          filename: res.filename,
          textPreview: res.extracted_text_preview || "",
        }));
        if (type === "CV") setCvDocumentId(res.id);
        else setJdDocumentId(res.id);
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          uploadStatus: "error",
          error: e instanceof Error ? e.message : "Upload thất bại. Kiểm tra backend đang chạy.",
        }));
      }
    },
    []
  );

  const handleParse = useCallback(
    async (
      state: DocState,
      setState: React.Dispatch<React.SetStateAction<DocState>>
    ) => {
      if (!state.docId) return;
      setState((s) => ({ ...s, parseStatus: "loading", error: "" }));
      try {
        const res = await parseDocument(state.docId);
        setState((s) => ({ ...s, parseStatus: "success", parsedData: res }));
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          parseStatus: "error",
          error: e instanceof Error ? e.message : "Parse thất bại. LLM có thể không phản hồi.",
        }));
      }
    },
    []
  );

  const handleIndex = useCallback(
    async (
      state: DocState,
      setState: React.Dispatch<React.SetStateAction<DocState>>
    ) => {
      if (!state.docId) return;
      setState((s) => ({ ...s, indexStatus: "loading", error: "" }));
      try {
        const res = await indexDocument(state.docId);
        setState((s) => ({
          ...s,
          indexStatus: "success",
          chunksIndexed: res.chunks_indexed,
        }));
      } catch (e: unknown) {
        setState((s) => ({
          ...s,
          indexStatus: "error",
          error: e instanceof Error ? e.message : "Index thất bại.",
        }));
      }
    },
    []
  );

  // ---------------------------------------------------------------
  // Start interview
  // ---------------------------------------------------------------

  const canStart =
    cv.indexStatus === "success" && jd.indexStatus === "success";

  const handleStartInterview = async () => {
    if (!cv.docId || !jd.docId) return;
    setInterviewLoading(true);
    setInterviewError("");
    try {
      const res = await startInterview(cv.docId, jd.docId);
      setSessionId(res.session_id);
      router.push(`/interview/${res.session_id}`);
    } catch (e: unknown) {
      setInterviewError(
        e instanceof Error ? e.message : "Không thể bắt đầu phỏng vấn."
      );
    } finally {
      setInterviewLoading(false);
    }
  };

  // ---------------------------------------------------------------
  // Reset demo
  // ---------------------------------------------------------------

  const handleReset = () => {
    clearAll();
    setCv({ ...initialDocState });
    setJd({ ...initialDocState });
    setInterviewError("");
  };

  // ---------------------------------------------------------------
  // File picker
  // ---------------------------------------------------------------

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setState: React.Dispatch<React.SetStateAction<DocState>>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setState((s) => ({
        ...s,
        error: `File không hợp lệ. Chỉ chấp nhận: ${ALLOWED.join(", ")}`,
      }));
      return;
    }
    setState({
      ...initialDocState,
      file,
      filename: file.name,
    });
  };

  // ---------------------------------------------------------------
  // Render a document setup card
  // ---------------------------------------------------------------

  const renderDocCard = (
    label: string,
    emoji: string,
    type: "CV" | "JD",
    state: DocState,
    setState: React.Dispatch<React.SetStateAction<DocState>>
  ) => {
    const allDone = state.indexStatus === "success";
    return (
      <Card className={allDone ? "ring-2 ring-emerald-200" : ""}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-lg">{emoji} {label}</h3>
          {allDone && (
            <span className="bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5 rounded-full">
              ✓ Sẵn sàng
            </span>
          )}
        </div>

        {state.error && (
          <ErrorAlert message={state.error} onDismiss={() => setState((s) => ({ ...s, error: "" }))} />
        )}

        {/* Step 1: Upload */}
        <div className="space-y-3 mt-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">1. Upload file</span>
            <StepStatusBadge status={state.uploadStatus} />
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => handleFileChange(e, setState)}
              className="text-sm file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 file:cursor-pointer cursor-pointer"
            />
            <LoadingButton
              loading={state.uploadStatus === "loading"}
              disabled={!state.file || state.uploadStatus === "success"}
              onClick={() => handleUpload(type, state, setState)}
              variant="primary"
            >
              Upload
            </LoadingButton>
          </div>
          {state.uploadStatus === "success" && (
            <div className="space-y-1">
              <SuccessAlert message={`ID: ${state.docId} · ${state.filename}`} />
              {state.textPreview && (
                <p className="text-xs text-gray-500 bg-gray-50 rounded p-2 line-clamp-3">
                  {state.textPreview}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Step 2: Parse */}
        <div className="space-y-3 mt-5 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">2. Parse bằng LLM</span>
            <StepStatusBadge status={state.parseStatus} />
          </div>
          {state.parseStatus === "loading" && (
            <p className="text-xs text-blue-600 animate-pulse">
              ⏳ AI đang phân tích nội dung... (có thể mất 10-30 giây)
            </p>
          )}
          <LoadingButton
            loading={state.parseStatus === "loading"}
            disabled={state.uploadStatus !== "success" || state.parseStatus === "success"}
            onClick={() => handleParse(state, setState)}
            variant="secondary"
          >
            Parse Document
          </LoadingButton>
          {state.parsedData && (
            <div>
              <button
                className="text-xs text-[var(--primary)] hover:underline cursor-pointer"
                onClick={() => setState((s) => ({ ...s, showJson: !s.showJson }))}
              >
                {state.showJson ? "▼ Ẩn JSON" : "▶ Xem Parsed JSON"}
              </button>
              {state.showJson && <JsonPreview data={state.parsedData.parsed_json} />}
            </div>
          )}
        </div>

        {/* Step 3: Index */}
        <div className="space-y-3 mt-5 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">3. Index vào Vector Store</span>
            <StepStatusBadge status={state.indexStatus} />
          </div>
          {state.indexStatus === "loading" && (
            <p className="text-xs text-blue-600 animate-pulse">
              ⏳ Đang tạo embeddings và lưu vào ChromaDB...
            </p>
          )}
          <LoadingButton
            loading={state.indexStatus === "loading"}
            disabled={state.parseStatus !== "success" || state.indexStatus === "success"}
            onClick={() => handleIndex(state, setState)}
            variant="secondary"
          >
            Index Document
          </LoadingButton>
          {state.indexStatus === "success" && (
            <SuccessAlert message={`${state.chunksIndexed} chunks indexed thành công`} />
          )}
        </div>
      </Card>
    );
  };

  // ---------------------------------------------------------------
  // Page
  // ---------------------------------------------------------------

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">📄 Document Setup</h1>
          <p className="text-[var(--muted)] mt-1">
            Upload, parse và index CV/JD trước khi bắt đầu phỏng vấn.
          </p>
        </div>
        <LoadingButton variant="secondary" onClick={handleReset}>
          🔄 Reset Demo
        </LoadingButton>
      </div>

      {/* Sample data tip */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <strong>💡 Mẹo:</strong> Dùng sample files cho demo nhanh: tải file từ{" "}
        <a
          href="/demo_samples/sample_cv_backend_intern.txt"
          download
          className="underline font-medium"
        >
          sample_cv_backend_intern.txt
        </a>{" "}
        và{" "}
        <a
          href="/demo_samples/sample_jd_backend_intern.txt"
          download
          className="underline font-medium"
        >
          sample_jd_backend_intern.txt
        </a>
        , sau đó upload bên dưới.
      </div>

      {/* Document cards */}
      <div className="grid md:grid-cols-2 gap-6">
        {renderDocCard("CV (Curriculum Vitae)", "📋", "CV", cv, setCv)}
        {renderDocCard("JD (Job Description)", "📝", "JD", jd, setJd)}
      </div>

      {/* Start Interview */}
      <Card className={`text-center ${canStart ? "ring-2 ring-emerald-200 bg-emerald-50/30" : ""}`}>
        <h3 className="font-semibold text-lg mb-2">🎤 Bắt đầu phỏng vấn</h3>
        <p className="text-sm text-[var(--muted)] mb-4">
          {canStart
            ? "CV và JD đã sẵn sàng! Nhấn nút bên dưới để bắt đầu."
            : "Cần hoàn thành cả 3 bước cho CV và JD trước khi bắt đầu."
          }
        </p>
        {interviewLoading && (
          <p className="text-xs text-blue-600 animate-pulse mb-2">
            ⏳ AI đang tạo câu hỏi phỏng vấn đầu tiên...
          </p>
        )}
        {interviewError && <ErrorAlert message={interviewError} onDismiss={() => setInterviewError("")} />}
        <LoadingButton
          loading={interviewLoading}
          disabled={!canStart}
          onClick={handleStartInterview}
          variant="success"
          className="mt-3"
        >
          Start Interview
        </LoadingButton>
      </Card>
    </div>
  );
}
