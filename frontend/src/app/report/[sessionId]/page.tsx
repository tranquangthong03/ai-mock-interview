"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  generateReport,
  getReport,
  getSummary,
  exportReport,
  downloadBlob,
} from "@/lib/api";
import {
  LoadingButton,
  ErrorAlert,
  Card,
  ScoreBar,
} from "@/components/ui";
import type { InterviewReport, InterviewSummary } from "@/types";

const criterionLabels: Record<string, string> = {
  relevance: "Relevance (Đúng trọng tâm)",
  clarity: "Clarity (Rõ ràng)",
  specificity: "Specificity (Cụ thể)",
  technical_accuracy: "Technical Accuracy (Kỹ thuật)",
  jd_alignment: "JD Alignment (Phù hợp JD)",
  communication: "Communication (Giao tiếp)",
};

export default function ReportPage() {
  const params = useParams();
  const sessionId = Number(params.sessionId);

  const [report, setReport] = useState<InterviewReport | null>(null);
  const [summary, setSummary] = useState<InterviewSummary | null>(null);
  const [generating, setGenerating] = useState(false);
  const [loadingReport, setLoadingReport] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [error, setError] = useState("");

  // Export states
  const [exportingMd, setExportingMd] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportError, setExportError] = useState("");

  // Load existing report + summary
  useEffect(() => {
    async function load() {
      try {
        const r = await getReport(sessionId);
        setReport(r);
      } catch {
        // No report yet — expected
      } finally {
        setLoadingReport(false);
      }

      try {
        const s = await getSummary(sessionId);
        setSummary(s);
      } catch {
        // No evaluations
      } finally {
        setLoadingSummary(false);
      }
    }
    if (sessionId) load();
  }, [sessionId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const r = await generateReport(sessionId);
      setReport(r);
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : "Không thể tạo báo cáo. Hãy kiểm tra session có evaluations."
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async (format: "markdown" | "pdf") => {
    const setLoading = format === "markdown" ? setExportingMd : setExportingPdf;
    setLoading(true);
    setExportError("");
    try {
      const blob = await exportReport(sessionId, format);
      const ext = format === "markdown" ? "md" : "pdf";
      downloadBlob(blob, `interview_report_session_${sessionId}.${ext}`);
    } catch (e: unknown) {
      setExportError(
        e instanceof Error
          ? e.message
          : "Không thể tải báo cáo. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  const isLoading = loadingReport || loadingSummary;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--primary)] border-t-transparent rounded-full" />
        <p className="text-sm text-[var(--muted)]">Đang tải báo cáo...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">📊 Báo cáo phỏng vấn</h1>
          <p className="text-sm text-[var(--muted)]">Session #{sessionId}</p>
        </div>
        <div className="flex gap-2">
          <a
            href={`/interview/${sessionId}`}
            className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            ← Interview
          </a>
          <a
            href="/setup"
            className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            🔄 Demo mới
          </a>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError("")} />}

      {/* Summary card */}
      {summary && (
        <Card>
          <h2 className="font-semibold text-lg mb-4">📈 Tóm tắt điểm số</h2>
          <div className="grid sm:grid-cols-3 gap-4 mb-5">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-[var(--primary)]">
                {summary.average_score.toFixed(1)}
              </div>
              <div className="text-xs text-[var(--muted)] mt-1">Điểm trung bình</div>
            </div>
            <div className="text-center p-4 bg-emerald-50 rounded-lg">
              <div className="text-sm font-semibold text-emerald-700">
                {criterionLabels[summary.best_criterion] || summary.best_criterion}
              </div>
              <div className="text-xs text-[var(--muted)] mt-1">🏆 Tiêu chí tốt nhất</div>
            </div>
            <div className="text-center p-4 bg-amber-50 rounded-lg">
              <div className="text-sm font-semibold text-amber-700">
                {criterionLabels[summary.weakest_criterion] || summary.weakest_criterion}
              </div>
              <div className="text-xs text-[var(--muted)] mt-1">⚠️ Cần cải thiện nhất</div>
            </div>
          </div>
          <div className="space-y-2">
            {Object.entries(summary.criterion_averages).map(([key, val]) => (
              <ScoreBar
                key={key}
                label={criterionLabels[key] || key}
                score={val as number}
              />
            ))}
          </div>
          <p className="text-xs text-[var(--muted)] mt-3">
            📝 Tổng số câu trả lời: {summary.total_answers}
          </p>
        </Card>
      )}

      {/* Generate or show report */}
      {!report ? (
        <Card className="text-center">
          <h2 className="font-semibold text-lg mb-2">📝 Báo cáo chi tiết</h2>
          <p className="text-sm text-[var(--muted)] mb-4">
            Tạo báo cáo AI phân tích điểm mạnh, điểm yếu, skill gaps và kế hoạch cải thiện.
          </p>
          {generating && (
            <p className="text-sm text-blue-600 animate-pulse mb-3">
              ⏳ AI đang phân tích và tạo báo cáo... (có thể mất 15-30 giây)
            </p>
          )}
          <LoadingButton
            loading={generating}
            onClick={handleGenerate}
            variant="primary"
          >
            🤖 Generate Report bằng AI
          </LoadingButton>
        </Card>
      ) : (
        <>
          {/* ── Export buttons ── */}
          <Card className="bg-gradient-to-r from-slate-50 to-gray-50 border-slate-200">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold text-sm text-slate-700">📥 Tải báo cáo</h3>
                <p className="text-xs text-[var(--muted)] mt-0.5">
                  Bạn có thể tải báo cáo để lưu lại kế hoạch cải thiện sau buổi phỏng vấn.
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <LoadingButton
                  loading={exportingMd}
                  onClick={() => handleExport("markdown")}
                  variant="secondary"
                  disabled={exportingPdf}
                >
                  📄 Tải Markdown
                </LoadingButton>
                <LoadingButton
                  loading={exportingPdf}
                  onClick={() => handleExport("pdf")}
                  variant="secondary"
                  disabled={exportingMd}
                >
                  📑 Tải PDF
                </LoadingButton>
              </div>
            </div>
            {exportError && (
              <div className="mt-3">
                <ErrorAlert message={exportError} onDismiss={() => setExportError("")} />
              </div>
            )}
          </Card>

          {/* Overall score */}
          <Card>
            <div className="flex items-center gap-4 mb-5">
              <div className="w-16 h-16 rounded-full bg-[var(--primary)] text-white flex items-center justify-center text-xl font-bold shadow-lg">
                {report.overall_score.toFixed(1)}
              </div>
              <div>
                <h2 className="font-semibold text-lg">Điểm tổng kết</h2>
                <p className="text-sm text-[var(--muted)]">Trên thang 10 · Đánh giá bởi AI</p>
              </div>
            </div>
            <div className="space-y-2">
              {Object.entries(report.criterion_scores).map(([key, val]) => (
                <ScoreBar
                  key={key}
                  label={criterionLabels[key] || key}
                  score={val as number}
                />
              ))}
            </div>
          </Card>

          {/* Summary text */}
          {report.summary && (
            <Card>
              <h3 className="font-semibold mb-2">📋 Tổng quan</h3>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{report.summary}</p>
            </Card>
          )}

          {/* Strengths */}
          {report.strengths_summary?.length > 0 && (
            <Card className="border-l-4 border-l-emerald-500">
              <h3 className="font-semibold mb-3 text-emerald-700">✅ Điểm mạnh</h3>
              <ul className="space-y-1.5">
                {report.strengths_summary.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-emerald-500 shrink-0">•</span>{s}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Weaknesses */}
          {report.weaknesses_summary?.length > 0 && (
            <Card className="border-l-4 border-l-amber-500">
              <h3 className="font-semibold mb-3 text-amber-700">⚠️ Điểm yếu</h3>
              <ul className="space-y-1.5">
                {report.weaknesses_summary.map((w, i) => (
                  <li key={i} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-amber-500 shrink-0">•</span>{w}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Skill Gaps */}
          {report.skill_gap_summary?.length > 0 && (
            <Card className="border-l-4 border-l-red-400">
              <h3 className="font-semibold mb-3 text-red-700">🔍 Skill Gaps</h3>
              <ul className="space-y-1.5">
                {report.skill_gap_summary.map((g, i) => (
                  <li key={i} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-red-400 shrink-0">•</span>{g}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Improvement Plan */}
          {report.improvement_plan?.length > 0 && (
            <Card className="border-l-4 border-l-blue-500">
              <h3 className="font-semibold mb-3 text-blue-700">📚 Kế hoạch cải thiện</h3>
              <ol className="space-y-1.5 list-decimal list-inside">
                {report.improvement_plan.map((p, i) => (
                  <li key={i} className="text-sm text-gray-700">{p}</li>
                ))}
              </ol>
            </Card>
          )}

          {/* Recommended Topics */}
          {report.recommended_topics?.length > 0 && (
            <Card>
              <h3 className="font-semibold mb-3">🎯 Chủ đề nên ôn tập</h3>
              <div className="flex flex-wrap gap-2">
                {report.recommended_topics.map((t, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </Card>
          )}

          {/* Final Advice */}
          {report.final_advice && (
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
              <h3 className="font-semibold mb-2 text-indigo-800">💡 Lời khuyên</h3>
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{report.final_advice}</p>
            </Card>
          )}

          {/* Regenerate */}
          <Card className="text-center">
            <p className="text-sm text-[var(--muted)] mb-3">
              Muốn tạo lại báo cáo với phân tích mới?
            </p>
            <LoadingButton
              loading={generating}
              onClick={handleGenerate}
              variant="secondary"
            >
              🔄 Regenerate Report
            </LoadingButton>
          </Card>
        </>
      )}

      {/* Footer navigation */}
      <div className="flex items-center justify-center gap-4 pb-8 text-sm">
        <a
          href={`/interview/${sessionId}`}
          className="text-[var(--primary)] hover:underline"
        >
          ← Xem lại phỏng vấn
        </a>
        <span className="text-gray-300">|</span>
        <a href="/setup" className="text-[var(--primary)] hover:underline">
          🔄 Bắt đầu phỏng vấn mới
        </a>
      </div>
    </div>
  );
}
