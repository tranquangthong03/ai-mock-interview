"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { indexDocument, parseDocument, startInterview, uploadDocument } from "@/lib/api";
import { clearAll, setCvDocumentId, setJdDocumentId, setSessionId } from "@/lib/local-storage";
import {
  AnimatedPage,
  Badge,
  Button,
  Card,
  ErrorAlert,
  FileUploadCard,
  JsonPreview,
  PageContainer,
  PageHeader,
  ProgressStep,
  SectionCard,
  StatusBadge,
  SuccessAlert,
  TechBackground,
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

const allowedExtensions = [".pdf", ".docx", ".txt"];

function nextStatus(statuses: StepStatus[]): StepStatus {
  if (statuses.includes("error")) return "error";
  if (statuses.includes("loading")) return "loading";
  if (statuses.every((status) => status === "success")) return "success";
  return "pending";
}

export default function SetupPage() {
  const router = useRouter();
  const [cv, setCv] = useState<DocState>({ ...initialDocState });
  const [jd, setJd] = useState<DocState>({ ...initialDocState });
  const [interviewLoading, setInterviewLoading] = useState(false);
  const [interviewError, setInterviewError] = useState("");

  const canStart = cv.indexStatus === "success" && jd.indexStatus === "success";

  const progress = useMemo<Array<{ title: string; status: StepStatus }>>(
    () => [
      { title: "Upload CV", status: cv.uploadStatus },
      { title: "Upload JD", status: jd.uploadStatus },
      { title: "Parse", status: nextStatus([cv.parseStatus, jd.parseStatus]) },
      { title: "Index", status: nextStatus([cv.indexStatus, jd.indexStatus]) },
      { title: "Start Interview", status: interviewLoading ? "loading" : canStart ? "success" : "pending" },
    ],
    [canStart, cv.indexStatus, cv.parseStatus, cv.uploadStatus, interviewLoading, jd.indexStatus, jd.parseStatus, jd.uploadStatus]
  );

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>,
    setState: React.Dispatch<React.SetStateAction<DocState>>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!allowedExtensions.includes(extension)) {
      setState((state) => ({
        ...state,
        error: `File không hợp lệ. Chỉ chấp nhận: ${allowedExtensions.join(", ")}`,
      }));
      return;
    }
    setState({ ...initialDocState, file, filename: file.name });
  };

  const handleUpload = useCallback(
    async (
      type: "CV" | "JD",
      state: DocState,
      setState: React.Dispatch<React.SetStateAction<DocState>>
    ) => {
      if (!state.file) return;
      setState((current) => ({ ...current, uploadStatus: "loading", error: "" }));
      try {
        const response = await uploadDocument(state.file, type);
        setState((current) => ({
          ...current,
          uploadStatus: "success",
          docId: response.id,
          filename: response.filename,
          textPreview: response.extracted_text_preview || "",
        }));
        if (type === "CV") setCvDocumentId(response.id);
        else setJdDocumentId(response.id);
      } catch (error: unknown) {
        setState((current) => ({
          ...current,
          uploadStatus: "error",
          error: error instanceof Error ? error.message : "Upload thất bại. Kiểm tra backend đang chạy.",
        }));
      }
    },
    []
  );

  const handleParse = useCallback(
    async (state: DocState, setState: React.Dispatch<React.SetStateAction<DocState>>) => {
      if (!state.docId) return;
      setState((current) => ({ ...current, parseStatus: "loading", error: "" }));
      try {
        const response = await parseDocument(state.docId);
        setState((current) => ({ ...current, parseStatus: "success", parsedData: response }));
      } catch (error: unknown) {
        setState((current) => ({
          ...current,
          parseStatus: "error",
          error: error instanceof Error ? error.message : "Parse thất bại. LLM có thể không phản hồi.",
        }));
      }
    },
    []
  );

  const handleIndex = useCallback(
    async (state: DocState, setState: React.Dispatch<React.SetStateAction<DocState>>) => {
      if (!state.docId) return;
      setState((current) => ({ ...current, indexStatus: "loading", error: "" }));
      try {
        const response = await indexDocument(state.docId);
        setState((current) => ({
          ...current,
          indexStatus: "success",
          chunksIndexed: response.chunks_indexed,
        }));
      } catch (error: unknown) {
        setState((current) => ({
          ...current,
          indexStatus: "error",
          error: error instanceof Error ? error.message : "Index thất bại.",
        }));
      }
    },
    []
  );

  const handleStartInterview = async () => {
    if (!cv.docId || !jd.docId) return;
    setInterviewLoading(true);
    setInterviewError("");
    try {
      const response = await startInterview(cv.docId, jd.docId);
      setSessionId(response.session_id);
      router.push(`/interview/${response.session_id}`);
    } catch (error: unknown) {
      setInterviewError(error instanceof Error ? error.message : "Không thể bắt đầu phỏng vấn.");
    } finally {
      setInterviewLoading(false);
    }
  };

  const handleReset = () => {
    clearAll();
    setCv({ ...initialDocState });
    setJd({ ...initialDocState });
    setInterviewError("");
  };

  const renderDocumentCard = (
    title: string,
    description: string,
    type: "CV" | "JD",
    state: DocState,
    setState: React.Dispatch<React.SetStateAction<DocState>>
  ) => {
    const ready = state.indexStatus === "success";
    return (
      <Card className={ready ? "ring-2 ring-emerald-200" : ""}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-500/30 bg-cyan-500/10 text-lg font-black text-cyan-200">
              {type}
            </div>
            <p className="text-lg font-bold text-slate-50">{title}</p>
            <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
          </div>
          <StatusBadge status={ready ? "ready" : state.error ? "error" : "pending"} />
        </div>

        <div className="mt-5 space-y-5">
          {state.error && <ErrorAlert message={state.error} onDismiss={() => setState((current) => ({ ...current, error: "" }))} />}

          <FileUploadCard
            label={`${type} file`}
            description="Supports .pdf, .docx, .txt"
            filename={state.filename}
            onChange={(event) => handleFileChange(event, setState)}
          />

          <div className="grid gap-3 sm:grid-cols-3">
            <Button
              type="button"
              loading={state.uploadStatus === "loading"}
              disabled={!state.file || state.uploadStatus === "success"}
              onClick={() => handleUpload(type, state, setState)}
            >
              Upload
            </Button>
            <Button
              type="button"
              variant="secondary"
              loading={state.parseStatus === "loading"}
              disabled={state.uploadStatus !== "success" || state.parseStatus === "success"}
              onClick={() => handleParse(state, setState)}
            >
              Parse
            </Button>
            <Button
              type="button"
              variant="secondary"
              loading={state.indexStatus === "loading"}
              disabled={state.parseStatus !== "success" || state.indexStatus === "success"}
              onClick={() => handleIndex(state, setState)}
            >
              Index
            </Button>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <StatusLine label="Upload" status={state.uploadStatus} />
            <StatusLine label="Parse" status={state.parseStatus} />
            <StatusLine label="Index" status={state.indexStatus} />
          </div>

          {state.uploadStatus === "success" && (
            <SuccessAlert message={`Document #${state.docId} · ${state.filename}`} />
          )}

          {state.textPreview && (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Extracted preview</p>
              <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-300">{state.textPreview}</p>
            </div>
          )}

          {state.parsedData && (
            <div className="animate-slide-up-fade rounded-2xl border border-cyan-500/30 bg-slate-950/60 p-4 shadow-sm shadow-cyan-950/20">
              <button
                type="button"
                onClick={() => setState((current) => ({ ...current, showJson: !current.showJson }))}
                className="flex w-full items-center justify-between text-left text-sm font-bold text-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                <span>Parsed JSON preview</span>
                <Badge tone="emerald">{state.showJson ? "Hide" : "Show"}</Badge>
              </button>
              {state.showJson && <div className="mt-4"><JsonPreview data={state.parsedData.parsed_json} /></div>}
            </div>
          )}

          {state.indexStatus === "success" && (
            <Badge tone="emerald">Indexed · {state.chunksIndexed} chunks ready</Badge>
          )}
        </div>
      </Card>
    );
  };

  return (
    <PageContainer className="space-y-8 overflow-hidden">
      <TechBackground />
      <AnimatedPage className="relative space-y-8">
      <PageHeader
        eyebrow="Onboarding workflow"
        title="Interview Setup"
        subtitle="Upload, parse, and index an English CV/JD before starting the technical interview. Use an English CV/JD for better interview questions."
        actions={
          <>
            <a
              href="/demo_samples/sample_cv_backend_intern.txt"
              download
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 shadow-sm hover:bg-slate-700"
            >
              Sample CV
            </a>
            <a
              href="/demo_samples/sample_jd_backend_intern.txt"
              download
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 shadow-sm hover:bg-slate-700"
            >
              Sample JD
            </a>
            <Button type="button" variant="outline" onClick={handleReset}>
              Reset
            </Button>
          </>
        }
      />

      <SectionCard className="relative overflow-hidden">
        <div className="scan-highlight absolute inset-x-0 top-0 h-px" aria-hidden="true" />
        <div className="grid gap-4 md:grid-cols-5">
          {progress.map((step, index) => (
            <ProgressStep key={step.title} index={index + 1} title={step.title} status={step.status} />
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        {renderDocumentCard("CV Upload", "Candidate profile, projects, skills, and experience.", "CV", cv, setCv)}
        {renderDocumentCard("Job Description Upload", "Target role, responsibilities, and required technical skills.", "JD", jd, setJd)}
      </div>

      <Card className={canStart ? "bg-emerald-500/10 ring-2 ring-emerald-500/30" : "bg-slate-900/80"}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold text-slate-50">Start technical interview</h2>
              {canStart ? <Badge tone="emerald">Ready</Badge> : <Badge tone="slate">Waiting for CV and JD</Badge>}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {canStart
                ? "Both documents are indexed. The first English interview question will be generated from the uploaded context."
                : "Complete upload, parse, and index for both CV and JD before starting."}
            </p>
            {interviewLoading && <p className="mt-2 text-sm text-blue-700">AI đang tạo câu hỏi phỏng vấn đầu tiên...</p>}
          </div>
          <Button
            type="button"
            variant="success"
            loading={interviewLoading}
            disabled={!canStart}
            onClick={handleStartInterview}
            className="w-full lg:w-auto"
          >
            Start Interview
          </Button>
        </div>
        {interviewError && <div className="mt-4"><ErrorAlert message={interviewError} onDismiss={() => setInterviewError("")} /></div>}
      </Card>
      </AnimatedPage>
    </PageContainer>
  );
}

function StatusLine({ label, status }: { label: string; status: StepStatus }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-2"><StatusBadge status={status} /></div>
    </div>
  );
}
