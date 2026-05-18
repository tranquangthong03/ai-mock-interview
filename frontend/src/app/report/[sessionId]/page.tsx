"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { downloadBlob, exportReport, generateReport, getReport, getSummary } from "@/lib/api";
import {
  AnimatedPage,
  Badge,
  Button,
  Card,
  CriteriaScoreGrid,
  EmptyState,
  ErrorAlert,
  InsightList,
  LoadingState,
  MetricCard,
  PageContainer,
  PageHeader,
  SectionCard,
  TechBackground,
} from "@/components/ui";
import type { InterviewReport, InterviewSummary } from "@/types";

const criterionLabels: Record<string, string> = {
  relevance: "Relevance (Đúng trọng tâm)",
  clarity: "Clarity (Rõ ràng)",
  specificity: "Specificity (Cụ thể)",
  technical_accuracy: "Technical accuracy (Kỹ thuật)",
  jd_alignment: "JD alignment (Phù hợp JD)",
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
  const [exportingMd, setExportingMd] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportError, setExportError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const existingReport = await getReport(sessionId);
        setReport(existingReport);
      } catch {
        // Report can be absent before the user generates it.
      } finally {
        setLoadingReport(false);
      }

      try {
        const existingSummary = await getSummary(sessionId);
        setSummary(existingSummary);
      } catch {
        // Summary can be absent if there are no evaluations yet.
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
      const response = await generateReport(sessionId);
      setReport(response);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : "Không thể tạo báo cáo. Hãy kiểm tra session có evaluations.");
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
      downloadBlob(blob, `interview_report_session_${sessionId}.${format === "markdown" ? "md" : "pdf"}`);
    } catch (error: unknown) {
      setExportError(error instanceof Error ? error.message : "Không thể tải báo cáo. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  if (loadingReport || loadingSummary) {
    return <LoadingState title="Đang tải báo cáo..." subtitle="Collecting summary, scores, and export readiness." />;
  }

  const strongest = summary?.best_criterion ? criterionLabels[summary.best_criterion] || summary.best_criterion : "Chưa có";
  const weakest = summary?.weakest_criterion ? criterionLabels[summary.weakest_criterion] || summary.weakest_criterion : "Chưa có";

  return (
    <PageContainer className="space-y-8 overflow-hidden">
      <TechBackground />
      <AnimatedPage className="relative space-y-8">
      <PageHeader
        eyebrow="Assessment dashboard"
        title="Interview Report"
        subtitle={`Báo cáo tổng kết buổi phỏng vấn · Session #${sessionId}`}
        actions={
          <>
            <Link
              href={`/interview/${sessionId}`}
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 shadow-sm hover:bg-slate-700"
            >
              Interview
            </Link>
            <Link
              href="/setup"
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-100 shadow-sm hover:bg-slate-700"
            >
              New Demo
            </Link>
          </>
        }
      />

      {error && <ErrorAlert message={error} onDismiss={() => setError("")} />}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Overall score"
          value={report ? report.overall_score.toFixed(1) : summary ? summary.average_score.toFixed(1) : "--"}
          helper="Scale 0-10"
          tone="blue"
        />
        <MetricCard label="Answered rounds" value={summary?.total_answers ?? 0} helper="Evaluated candidate answers" tone="emerald" />
        <MetricCard label="Strongest criterion" value={<SmallMetricText>{strongest}</SmallMetricText>} tone="indigo" />
        <MetricCard label="Weakest criterion" value={<SmallMetricText>{weakest}</SmallMetricText>} tone="amber" />
      </div>

      {summary && (
        <SectionCard className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-slate-50">Criteria averages</h2>
              <p className="mt-1 text-sm text-slate-400">Điểm trung bình theo 6 tiêu chí đánh giá.</p>
            </div>
            <Badge tone="blue">Average {summary.average_score.toFixed(1)}/10</Badge>
          </div>
          <CriteriaScoreGrid scores={summary.criterion_averages} />
        </SectionCard>
      )}

      <SectionCard className="relative overflow-hidden">
        <div className="scan-highlight absolute inset-x-0 top-0 h-px" aria-hidden="true" />
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-50">Report actions</h2>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Generate or regenerate the Vietnamese report, then export Markdown/PDF.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button type="button" loading={generating} onClick={handleGenerate}>
              {report ? "Regenerate" : "Generate Report"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              loading={exportingMd}
              disabled={!report || exportingPdf}
              onClick={() => handleExport("markdown")}
            >
              Export Markdown
            </Button>
            <Button
              type="button"
              variant="secondary"
              loading={exportingPdf}
              disabled={!report || exportingMd}
              onClick={() => handleExport("pdf")}
            >
              Export PDF
            </Button>
          </div>
        </div>
        {generating && <p className="mt-4 text-sm text-blue-700">AI đang phân tích và tạo báo cáo tiếng Việt...</p>}
        {exportError && <div className="mt-4"><ErrorAlert message={exportError} onDismiss={() => setExportError("")} /></div>}
      </SectionCard>

      {!report ? (
        <EmptyState
          title="Chưa có báo cáo chi tiết"
          description="Nhấn Generate Report để tạo báo cáo tiếng Việt từ các evaluation hiện có của session."
          action={
            <Button type="button" loading={generating} onClick={handleGenerate}>
              Generate Report
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="min-w-0 space-y-5">
            {report.summary && (
              <ReportSection title="Tổng quan" tone="blue">
                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{report.summary}</p>
              </ReportSection>
            )}

            <div className="grid gap-5 lg:grid-cols-2">
              <InsightList title="Điểm mạnh" items={report.strengths_summary} tone="emerald" />
              <InsightList title="Điểm yếu" items={report.weaknesses_summary} tone="amber" />
            </div>

            <ReportSection title="Khoảng trống kỹ năng" tone="red">
              <BulletList items={report.skill_gap_summary} />
            </ReportSection>

            <ReportSection title="Kế hoạch cải thiện" tone="indigo">
              <NumberedList items={report.improvement_plan} />
            </ReportSection>

            <ReportSection title="Chủ đề nên ôn tập" tone="violet">
              <div className="flex flex-wrap gap-2">
                {report.recommended_topics.map((topic, index) => (
                  <Badge key={`${topic}-${index}`} tone="violet">{topic}</Badge>
                ))}
              </div>
            </ReportSection>

            {report.final_advice && (
              <ReportSection title="Lời khuyên cuối cùng" tone="emerald">
                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{report.final_advice}</p>
              </ReportSection>
            )}
          </main>

          <aside className="space-y-5 xl:sticky xl:top-24 xl:self-start">
            <Card className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-slate-50">Final scores</h2>
                <Badge tone="blue">{report.overall_score.toFixed(1)}/10</Badge>
              </div>
              <CriteriaScoreGrid scores={report.criterion_scores} />
            </Card>
            <Card className="bg-slate-950 text-white">
              <h2 className="text-sm font-bold">Report language</h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Evaluation and report content remain Vietnamese. Interview questions and candidate answers remain English.
              </p>
            </Card>
          </aside>
        </div>
      )}
      </AnimatedPage>
    </PageContainer>
  );
}

function SmallMetricText({ children }: { children: React.ReactNode }) {
  return <span className="block text-base font-bold leading-6">{children}</span>;
}

function ReportSection({
  title,
  tone,
  children,
}: {
  title: string;
  tone: "blue" | "indigo" | "violet" | "emerald" | "amber" | "red";
  children: React.ReactNode;
}) {
  const toneMap = {
    blue: "border-blue-100",
    indigo: "border-indigo-100",
    violet: "border-violet-100",
    emerald: "border-emerald-100",
    amber: "border-amber-100",
    red: "border-red-100",
  };
  return (
    <SectionCard className={toneMap[tone]}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-50">{title}</h2>
        <Badge tone={tone}>Report</Badge>
      </div>
      {children}
    </SectionCard>
  );
}

function BulletList({ items }: { items?: string[] }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-slate-500">Chưa có dữ liệu.</p>;
  }
  return (
    <ul className="space-y-2 text-sm leading-7 text-slate-300">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2">
          <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-600" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function NumberedList({ items }: { items?: string[] }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-slate-500">Chưa có dữ liệu.</p>;
  }
  return (
    <ol className="space-y-3 text-sm leading-7 text-slate-300">
      {items.map((item, index) => (
        <li key={index} className="flex gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-xs font-bold text-white">
            {index + 1}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  );
}
