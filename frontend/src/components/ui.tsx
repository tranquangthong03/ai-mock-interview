"use client";

import React from "react";

// -----------------------------------------------------------------------
// LoadingButton
// -----------------------------------------------------------------------
export function LoadingButton({
  children,
  loading = false,
  disabled = false,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  variant?: "primary" | "secondary" | "danger" | "success";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
  const variants = {
    primary: "bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]",
    secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300",
    danger: "bg-red-600 text-white hover:bg-red-700",
    success: "bg-emerald-600 text-white hover:bg-emerald-700",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={loading || disabled}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
}

// -----------------------------------------------------------------------
// ErrorAlert
// -----------------------------------------------------------------------
export function ErrorAlert({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
      <span className="shrink-0 mt-0.5">⚠️</span>
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-400 hover:text-red-600 cursor-pointer">✕</button>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// SuccessAlert
// -----------------------------------------------------------------------
export function SuccessAlert({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
      <span>✅</span>
      <span>{message}</span>
    </div>
  );
}

// -----------------------------------------------------------------------
// StepStatusBadge
// -----------------------------------------------------------------------
export function StepStatusBadge({ status }: { status: "pending" | "loading" | "success" | "error" }) {
  const styles = {
    pending: "bg-gray-100 text-gray-500",
    loading: "bg-blue-100 text-blue-600 animate-pulse",
    success: "bg-emerald-100 text-emerald-700",
    error: "bg-red-100 text-red-600",
  };
  const labels = {
    pending: "Chờ",
    loading: "Đang xử lý...",
    success: "Hoàn tất",
    error: "Lỗi",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

// -----------------------------------------------------------------------
// ScoreBar
// -----------------------------------------------------------------------
export function ScoreBar({ label, score, max = 10 }: { label: string; score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    score >= 7 ? "bg-emerald-500" : score >= 5 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 w-40 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-200 rounded-full h-2.5 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold w-10 text-right">{score.toFixed(1)}</span>
    </div>
  );
}

// -----------------------------------------------------------------------
// Card wrapper
// -----------------------------------------------------------------------
export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-white rounded-xl border border-[var(--border)] shadow-sm p-5 ${className}`}>
      {children}
    </div>
  );
}

// -----------------------------------------------------------------------
// JsonPreview
// -----------------------------------------------------------------------
export function JsonPreview({ data }: { data: unknown }) {
  return (
    <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs overflow-x-auto max-h-64 overflow-y-auto">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// -----------------------------------------------------------------------
// SpeechMetricsCard
// -----------------------------------------------------------------------
export function SpeechMetricsCard({ metrics }: { metrics: {
  duration_seconds: number;
  word_count: number;
  speech_rate_wpm: number;
  filler_words: string[];
  filler_word_count: number;
  estimated_pause_count: number;
  notes: string[];
}}) {
  return (
    <div className="bg-violet-50/50 border border-violet-200 rounded-lg p-4 space-y-3">
      <h4 className="font-semibold text-sm text-violet-800">
        🎙️ Chỉ số trình bày qua giọng nói
      </h4>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-white rounded-lg p-2">
          <div className="text-lg font-bold text-violet-700">
            {metrics.duration_seconds.toFixed(1)}s
          </div>
          <div className="text-xs text-gray-500">Thời lượng</div>
        </div>
        <div className="bg-white rounded-lg p-2">
          <div className="text-lg font-bold text-violet-700">
            {metrics.word_count}
          </div>
          <div className="text-xs text-gray-500">Số từ</div>
        </div>
        <div className="bg-white rounded-lg p-2">
          <div className="text-lg font-bold text-violet-700">
            {metrics.speech_rate_wpm.toFixed(0)}
          </div>
          <div className="text-xs text-gray-500">Từ/phút</div>
        </div>
      </div>

      {metrics.filler_word_count > 0 && (
        <div className="text-xs">
          <span className="font-medium text-amber-700">Từ đệm ({metrics.filler_word_count}):</span>{" "}
          <span className="text-gray-600">
            {metrics.filler_words.map((w, i) => (
              <span key={i} className="bg-amber-100 text-amber-800 rounded px-1 mr-1 inline-block">
                {w}
              </span>
            ))}
          </span>
        </div>
      )}

      {metrics.notes.length > 0 && (
        <ul className="text-xs text-gray-600 space-y-0.5">
          {metrics.notes.map((n, i) => (
            <li key={i} className="flex gap-1">
              <span className="text-violet-400">💡</span>{n}
            </li>
          ))}
        </ul>
      )}

      <p className="text-[10px] text-gray-400 italic">
        Các chỉ số này chỉ hỗ trợ luyện tập cách trình bày, không phải kết luận chính xác về năng lực hay sự tự tin.
      </p>
    </div>
  );
}
