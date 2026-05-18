"use client";

import React from "react";
import type { Evaluation, EvaluationScores, SpeechMetrics } from "@/types";

type ButtonVariant = "primary" | "secondary" | "outline" | "danger" | "success" | "ghost";
type BadgeTone = "slate" | "blue" | "indigo" | "violet" | "emerald" | "amber" | "red";
type StepStatus = "pending" | "loading" | "success" | "error";

const criterionLabels: Record<keyof EvaluationScores, string> = {
  relevance: "Relevance",
  clarity: "Clarity",
  specificity: "Specificity",
  technical_accuracy: "Technical accuracy",
  jd_alignment: "JD alignment",
  communication: "Communication",
};

export const scoreLabels = criterionLabels;

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function LoadingSpinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block animate-spin rounded-full border-2 border-current border-t-transparent",
        className
      )}
      aria-hidden="true"
    />
  );
}

export function AnimatedPage({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("animate-slide-up-fade", className)}>{children}</div>;
}

export function TechBackground({ className = "" }: { className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)} aria-hidden="true">
      <div className="tech-grid absolute inset-0 opacity-60" />
      <div className="dot-matrix absolute inset-0 opacity-40" />
      <div className="animate-glow-shift absolute -left-24 top-8 h-72 w-72 rounded-full bg-cyan-300/25 blur-3xl" />
      <div className="animate-glow-shift absolute right-0 top-20 h-80 w-80 rounded-full bg-indigo-400/20 blur-3xl [animation-delay:1.2s]" />
      <div className="animate-glow-shift absolute bottom-0 left-1/2 h-64 w-64 rounded-full bg-violet-400/15 blur-3xl [animation-delay:2.1s]" />
    </div>
  );
}

export function Button({
  children,
  loading = false,
  disabled = false,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  variant?: ButtonVariant;
}) {
  const variants: Record<ButtonVariant, string> = {
    primary:
      "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/15 hover:bg-cyan-400 hover:shadow-cyan-500/25",
    secondary:
      "bg-slate-800 text-slate-100 border border-slate-700 shadow-sm hover:bg-slate-700",
    outline:
      "bg-transparent text-cyan-200 border border-cyan-500/40 hover:bg-cyan-500/10",
    danger:
      "bg-rose-500 text-white shadow-sm shadow-rose-500/20 hover:bg-rose-400",
    success:
      "bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/20 hover:bg-emerald-400",
    ghost:
      "bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white",
  };

  return (
    <button
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2",
        "hover:-translate-y-0.5 active:translate-y-0 disabled:cursor-not-allowed disabled:border disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-500 disabled:shadow-none disabled:hover:translate-y-0",
        variants[variant],
        className
      )}
      disabled={loading || disabled}
      {...props}
    >
      {loading && <LoadingSpinner />}
      {children}
    </button>
  );
}

export const LoadingButton = Button;
export const GradientButton = Button;

export function Card({
  children,
  className = "",
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-slate-800 bg-slate-900/80 p-5 shadow-[0_18px_55px_rgba(0,0,0,0.28)] backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-cyan-500/40 hover:shadow-[0_24px_70px_rgba(34,211,238,0.10)]",
        className
      )}
      style={style}
    >
      {children}
    </div>
  );
}

export const GlassCard = Card;

export function SectionCard({
  children,
  className = "",
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <section
      className={cn("rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-sm shadow-black/20 backdrop-blur transition duration-300 hover:border-cyan-500/40 hover:shadow-lg hover:shadow-cyan-950/20", className)}
      style={style}
    >
      {children}
    </section>
  );
}

export function PageContainer({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8", className)}>{children}</div>;
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  className = "",
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow && <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-300">{eyebrow}</p>}
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300 sm:text-base">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "slate",
  className = "",
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  const tones: Record<BadgeTone, string> = {
    slate: "bg-slate-800 text-slate-200 ring-slate-700",
    blue: "bg-blue-500/15 text-blue-200 ring-blue-500/30",
    indigo: "bg-indigo-500/15 text-indigo-200 ring-indigo-500/30",
    violet: "bg-violet-500/15 text-violet-200 ring-violet-500/30",
    emerald: "bg-emerald-500/15 text-emerald-200 ring-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-200 ring-amber-500/30",
    red: "bg-rose-500/15 text-rose-200 ring-rose-500/30",
  };

  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1", tones[tone], className)}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: StepStatus | "online" | "offline" | "ready" | "active" | "completed" }) {
  const map: Record<string, { tone: BadgeTone; label: string }> = {
    pending: { tone: "slate", label: "Pending" },
    loading: { tone: "blue", label: "Processing" },
    success: { tone: "emerald", label: "Complete" },
    error: { tone: "red", label: "Error" },
    online: { tone: "emerald", label: "Online" },
    offline: { tone: "red", label: "Offline" },
    ready: { tone: "emerald", label: "Ready" },
    active: { tone: "blue", label: "In progress" },
    completed: { tone: "slate", label: "Completed" },
  };
  const item = map[status];
  const active = status === "online" || status === "active" || status === "loading";
  return (
    <Badge tone={item.tone}>
      <span className={cn("h-1.5 w-1.5 rounded-full bg-current", active && "animate-pulse")} />
      {item.label}
    </Badge>
  );
}

export function StepStatusBadge({ status }: { status: StepStatus }) {
  return <StatusBadge status={status} />;
}

export function ProgressStep({
  index,
  title,
  status,
}: {
  index: number;
  title: string;
  status: StepStatus;
}) {
  const active = status === "loading" || status === "success";
  return (
    <div className="animate-slide-up-fade flex min-w-0 items-center gap-3">
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl text-sm font-bold",
          active ? "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20" : "bg-slate-800 text-slate-500"
        )}
      >
        {status === "success" ? "✓" : index}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-slate-100">{title}</p>
        <StatusBadge status={status} />
      </div>
    </div>
  );
}

export function ErrorAlert({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-500/20 text-xs font-bold">!</span>
        <p className="flex-1 leading-6">{message}</p>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-lg px-2 text-rose-200 hover:bg-rose-500/20 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
            aria-label="Dismiss error"
          >
            x
          </button>
        )}
      </div>
    </div>
  );
}

export function SuccessAlert({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
      <span className="font-semibold">Done:</span> {message}
    </div>
  );
}

export function LoadingState({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center gap-3 text-center">
      <LoadingSpinner className="h-8 w-8 text-cyan-300" />
      <div>
        <p className="font-semibold text-slate-50">{title}</p>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
      <p className="text-lg font-bold text-slate-50">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  helper,
  tone = "blue",
}: {
  label: string;
  value: React.ReactNode;
  helper?: string;
  tone?: BadgeTone;
}) {
  const accents: Record<BadgeTone, string> = {
    slate: "bg-slate-900/70 text-slate-100",
    blue: "bg-blue-500/10 text-blue-200",
    indigo: "bg-indigo-500/10 text-indigo-200",
    violet: "bg-violet-500/10 text-violet-200",
    emerald: "bg-emerald-500/10 text-emerald-200",
    amber: "bg-amber-500/10 text-amber-200",
    red: "bg-rose-500/10 text-rose-200",
  };
  return (
    <div className={cn("relative overflow-hidden rounded-2xl border border-slate-800 p-4 transition duration-300 hover:-translate-y-0.5 hover:border-cyan-500/40 hover:shadow-lg hover:shadow-cyan-950/20", accents[tone])}>
      <div className="scan-highlight absolute inset-x-0 top-0 h-px opacity-70" aria-hidden="true" />
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="mt-2 text-2xl font-bold tracking-tight">{value}</div>
      {helper && <p className="mt-1 text-xs leading-5 text-slate-400">{helper}</p>}
    </div>
  );
}

export function ScoreBar({ label, score, max = 10 }: { label: string; score: number; max?: number }) {
  const safeScore = Number.isFinite(score) ? score : 0;
  const pct = Math.max(0, Math.min(100, (safeScore / max) * 100));
  const tone =
    safeScore >= 7
      ? "bg-emerald-400"
      : safeScore >= 5
        ? "bg-amber-400"
        : "bg-rose-400";
  return (
    <div className="grid gap-2 sm:grid-cols-[minmax(150px,220px)_1fr_48px] sm:items-center">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <div className="h-3 overflow-hidden rounded-full bg-slate-800">
        <div className={cn("animate-score-fill h-full rounded-full transition-all duration-700", tone)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-right text-sm font-bold text-slate-100">{safeScore.toFixed(1)}</span>
    </div>
  );
}

export function CriteriaScoreGrid({ scores }: { scores: EvaluationScores }) {
  return (
    <div className="space-y-3">
      {Object.entries(scores).map(([key, value]) => (
        <ScoreBar key={key} label={criterionLabels[key as keyof EvaluationScores]} score={value as number} />
      ))}
    </div>
  );
}

export function JsonPreview({ data }: { data: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-2xl border border-cyan-400/20 bg-slate-950 p-4 text-xs leading-5 text-cyan-50 shadow-inner shadow-cyan-950/40">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function FileUploadCard({
  label,
  description,
  filename,
  accept = ".pdf,.docx,.txt",
  onChange,
}: {
  label: string;
  description: string;
  filename?: string;
  accept?: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="group block cursor-pointer rounded-3xl border border-dashed border-slate-700 bg-slate-950/50 p-5 transition duration-300 hover:-translate-y-0.5 hover:border-cyan-500/60 hover:shadow-lg hover:shadow-cyan-950/20">
      <span className="block text-sm font-bold text-slate-50">{label}</span>
      <span className="mt-1 block text-sm leading-6 text-slate-400">{description}</span>
      <span className="mt-4 inline-flex rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-cyan-200 shadow-sm ring-1 ring-slate-700 transition group-hover:bg-cyan-500 group-hover:text-slate-950">
        Choose file
      </span>
      <input type="file" accept={accept} onChange={onChange} className="sr-only" />
      {filename && <span className="mt-3 block truncate text-sm font-medium text-slate-200">{filename}</span>}
    </label>
  );
}

export function SpeechMetricsGrid({ metrics }: { metrics: SpeechMetrics }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Duration" value={`${metrics.duration_seconds.toFixed(1)}s`} tone="violet" />
      <MetricCard label="Word count" value={metrics.word_count} tone="blue" />
      <MetricCard label="Speaking rate" value={`${metrics.speech_rate_wpm.toFixed(0)} wpm`} tone="indigo" />
      <MetricCard label="Fillers" value={metrics.filler_word_count} helper={`${metrics.estimated_pause_count} pauses estimated`} tone="amber" />
    </div>
  );
}

export function AudioWave({ active = true }: { active?: boolean }) {
  const bars = [18, 30, 22, 38, 26, 44, 24, 34, 20];
  return (
    <div className="flex h-12 items-center gap-1.5 rounded-2xl border border-cyan-500/30 bg-slate-950 px-4 shadow-inner shadow-cyan-950/40" aria-hidden="true">
      {bars.map((height, index) => (
        <span
          key={index}
          className={cn("wave-bar w-1.5 rounded-full bg-cyan-400", !active && "opacity-40")}
          style={{
            height,
            animationDelay: `${index * 90}ms`,
            animationPlayState: active ? "running" : "paused",
          }}
        />
      ))}
    </div>
  );
}

export function TechIllustration() {
  return (
    <div className="relative min-h-[420px] overflow-hidden rounded-3xl border border-white/70 bg-slate-950 p-6 text-white shadow-[0_30px_90px_rgba(15,23,42,0.35)]">
      <div className="tech-grid absolute inset-0 opacity-20" />
      <div className="animate-glow-shift absolute -right-10 top-0 h-52 w-52 rounded-full bg-cyan-400/20 blur-3xl" />
      <div className="animate-glow-shift absolute bottom-0 left-0 h-56 w-56 rounded-full bg-violet-500/20 blur-3xl [animation-delay:1.4s]" />
      <div className="relative space-y-4">
        <div className="animate-float-soft rounded-3xl border border-cyan-400/25 bg-white/10 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/50 bg-cyan-500 text-sm font-black text-slate-950">
                AI
              </div>
              <div>
                <p className="font-bold">AI Interviewer</p>
                <p className="text-xs text-cyan-100">Technical round · English</p>
              </div>
            </div>
            <Badge tone="emerald">Live</Badge>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-200">
            Explain how you would design a scalable API for candidate assessment.
          </p>
        </div>

        <div className="animate-float-soft ml-10 rounded-3xl border border-blue-400/20 bg-blue-500/10 p-4 backdrop-blur [animation-delay:0.6s]">
          <p className="font-mono text-xs text-cyan-200">const rubric = evaluate(answer, jdContext);</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
            <span className="rounded-xl bg-white/10 px-2 py-2">RAG</span>
            <span className="rounded-xl bg-white/10 px-2 py-2">STT</span>
            <span className="rounded-xl bg-white/10 px-2 py-2">Report</span>
          </div>
        </div>

        <div className="animate-float-soft grid grid-cols-2 gap-3 [animation-delay:1s]">
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
            <p className="text-xs text-slate-300">Score</p>
            <p className="mt-1 text-3xl font-black text-cyan-300">8.4</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
            <p className="mb-2 text-xs text-slate-300">Voice signal</p>
            <AudioWave active />
          </div>
        </div>
      </div>
    </div>
  );
}

export function SpeechMetricsCard({ metrics }: { metrics: SpeechMetrics }) {
  return (
    <SectionCard className="space-y-4 bg-slate-900/80">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-bold text-slate-50">Speech metrics</h4>
        <Badge tone="violet">Voice answer</Badge>
      </div>
      <SpeechMetricsGrid metrics={metrics} />
      {metrics.filler_word_count > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Filler words</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {metrics.filler_words.map((word, index) => (
              <Badge key={`${word}-${index}`} tone="amber">
                {word}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {metrics.notes.length > 0 && (
        <ul className="space-y-1 text-sm text-slate-300">
          {metrics.notes.map((note, index) => (
            <li key={index}>• {note}</li>
          ))}
        </ul>
      )}
      <p className="text-xs leading-5 text-slate-500">
        Các chỉ số giọng nói chỉ hỗ trợ luyện tập cách trình bày, không phải kết luận tuyệt đối về năng lực.
      </p>
    </SectionCard>
  );
}

export function EvaluationPanel({
  evaluation,
  expanded,
  onToggle,
}: {
  evaluation: Evaluation;
  expanded: boolean;
  onToggle?: () => void;
}) {
  return (
    <SectionCard className="space-y-4 bg-slate-900/80">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-slate-50">Đánh giá câu trả lời</p>
          <p className="mt-1 text-sm leading-6 text-slate-300">{evaluation.short_feedback}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone="indigo">Overall {evaluation.score_overall.toFixed(1)}/10</Badge>
          {onToggle && (
            <Button type="button" variant="ghost" onClick={onToggle} className="min-h-8 px-3 py-1">
              {expanded ? "Thu gọn" : "Chi tiết"}
            </Button>
          )}
        </div>
      </div>
      {expanded && (
        <div className="space-y-5">
          <CriteriaScoreGrid scores={evaluation.scores} />
          <div className="grid gap-3 lg:grid-cols-2">
            <InsightList title="Điểm mạnh" items={evaluation.strengths} tone="emerald" />
            <InsightList title="Cần cải thiện" items={evaluation.weaknesses} tone="amber" />
          </div>
          <InsightList title="Gợi ý cải thiện" items={evaluation.suggestions} tone="blue" />
          {evaluation.improved_answer_suggestion && (
            <div className="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-4">
              <p className="text-sm font-bold text-indigo-100">Câu trả lời mẫu</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                {evaluation.improved_answer_suggestion}
              </p>
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}

export function InsightList({
  title,
  items,
  tone = "blue",
}: {
  title: string;
  items?: string[];
  tone?: BadgeTone;
}) {
  if (!items || items.length === 0) return null;
  const tones: Record<BadgeTone, string> = {
    slate: "border-slate-700 bg-slate-800/60 text-slate-100",
    blue: "border-blue-500/30 bg-blue-500/10 text-blue-100",
    indigo: "border-indigo-500/30 bg-indigo-500/10 text-indigo-100",
    violet: "border-violet-500/30 bg-violet-500/10 text-violet-100",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-100",
    red: "border-rose-500/30 bg-rose-500/10 text-rose-100",
  };
  return (
    <div className={cn("rounded-2xl border p-4", tones[tone])}>
      <p className="text-sm font-bold">{title}</p>
      <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-300">
        {items.map((item, index) => (
          <li key={index} className="flex gap-2">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-current" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
