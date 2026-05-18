"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { checkBackendHealth, getBaseUrl } from "@/lib/api";
import {
  AnimatedPage,
  Badge,
  Card,
  MetricCard,
  PageContainer,
  SectionCard,
  StatusBadge,
  TechBackground,
  TechIllustration,
} from "@/components/ui";

const workflow = [
  ["Upload CV & JD", "Prepare candidate and job context."],
  ["Parse candidate profile", "Extract structured skills, projects, and requirements."],
  ["Index interview context", "Store context for RAG-based question generation."],
  ["AI asks English questions", "Run a focused technical interview round."],
  ["Vietnamese evaluation", "Score each answer and explain feedback in Vietnamese."],
  ["Export final report", "Generate Markdown/PDF reports for review."],
];

const features = [
  ["English technical questions", "Interview prompts stay in English for realistic practice."],
  ["Voice answer with STT", "Record spoken answers and convert them to transcript."],
  ["Speech metrics", "Track duration, word count, pace, fillers, and pauses."],
  ["RAG-based context", "Questions are grounded in CV and job description content."],
  ["Vietnamese feedback", "Evaluation and improvement guidance are easy to present."],
  ["Markdown/PDF export", "Download a final report for demo or review."],
];

export default function Home() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    checkBackendHealth().then(setBackendOk);
  }, []);

  return (
    <PageContainer className="space-y-12 overflow-hidden">
      <TechBackground />
      <AnimatedPage className="relative space-y-12">
        <section className="grid items-center gap-8 py-8 lg:grid-cols-[1.05fr_0.95fr] lg:py-14">
          <div className="space-y-6">
            <Badge tone="blue">AI Interview Platform · Developer Assessment</Badge>
            <div className="space-y-4">
              <h1 className="max-w-4xl text-5xl font-black tracking-tight text-slate-50 lg:text-7xl">
                AI Mock Interviewer for Tech Candidates
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-300">
                Practice English technical interviews with AI-generated questions, voice answers,
                Vietnamese feedback, and detailed reports.
              </p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/setup"
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/15 transition hover:-translate-y-0.5 hover:bg-cyan-400 hover:shadow-cyan-500/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
              >
                Start Interview Setup
              </Link>
              <a
                href="#workflow"
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-cyan-500/40 bg-transparent px-5 py-2.5 text-sm font-bold text-cyan-200 shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:bg-cyan-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
              >
                Explore Workflow
              </a>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <MetricCard label="Language flow" value="EN → VI" helper="English interview, Vietnamese feedback" tone="indigo" />
              <MetricCard label="Rubric" value="6" helper="Criteria scored after each answer" tone="blue" />
              <MetricCard label="Exports" value="MD/PDF" helper="Report artifacts for demo" tone="violet" />
            </div>
          </div>
          <TechIllustration />
        </section>

        <SectionCard className="relative overflow-hidden">
          <div className="scan-highlight absolute inset-x-0 top-0 h-px" aria-hidden="true" />
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-slate-50">Backend health</h2>
              <p className="mt-1 text-sm text-slate-300">
                Current API endpoint: <code className="rounded-lg bg-slate-800 px-2 py-1 text-xs text-slate-200">{getBaseUrl()}</code>
              </p>
            </div>
            <StatusBadge status={backendOk === null ? "loading" : backendOk ? "online" : "offline"} />
          </div>
          {backendOk === false && (
            <p className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100">
              Không kết nối được backend. Hãy chạy FastAPI backend rồi tải lại trang trước khi demo.
            </p>
          )}
        </SectionCard>

        <section id="workflow" className="space-y-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600">Workflow</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-50">From documents to interview report</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workflow.map(([title, description], index) => (
              <Card key={title} className="animate-slide-up-fade" style={{ animationDelay: `${index * 80}ms` }}>
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-cyan-500 text-sm font-black text-slate-950 shadow-lg shadow-cyan-500/20">
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-50">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-5 pb-10">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600">Capabilities</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-50">Built for a complete AI interview demo</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {features.map(([title, description], index) => (
              <SectionCard key={title} className="animate-slide-up-fade" style={{ animationDelay: `${index * 70}ms` }}>
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-500/30 bg-cyan-500/10 text-sm font-black text-cyan-200">
                  {index + 1}
                </div>
                <h3 className="font-bold text-slate-50">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
              </SectionCard>
            ))}
          </div>
        </section>
      </AnimatedPage>
    </PageContainer>
  );
}
