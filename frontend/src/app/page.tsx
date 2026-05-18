"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { checkBackendHealth, getBaseUrl } from "@/lib/api";

const steps = [
  { num: 1, icon: "📄", title: "Upload CV & JD", desc: "Tải lên file CV và mô tả công việc (PDF, DOCX, TXT)" },
  { num: 2, icon: "🔍", title: "Parse & Index", desc: "AI phân tích nội dung và lưu vào vector store (ChromaDB)" },
  { num: 3, icon: "🎤", title: "Phỏng vấn", desc: "Trả lời câu hỏi từ AI Interviewer theo ngữ cảnh CV/JD" },
  { num: 4, icon: "📊", title: "Đánh giá", desc: "Nhận feedback chi tiết theo 6 tiêu chí sau mỗi câu trả lời" },
  { num: 5, icon: "📋", title: "Báo cáo", desc: "Xem tổng kết, skill gaps và kế hoạch cải thiện cá nhân hóa" },
];

export default function Home() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    checkBackendHealth().then(setBackendOk);
  }, []);

  return (
    <div className="max-w-3xl mx-auto space-y-10">
      {/* Hero */}
      <section className="text-center space-y-4 pt-6">
        <h1 className="text-4xl font-bold tracking-tight">
          🎤 AI Mock Interviewer
        </h1>
        <p className="text-lg text-[var(--muted)] max-w-xl mx-auto leading-relaxed">
          Luyện phỏng vấn kỹ thuật với AI — nhận đánh giá chi tiết theo 6 tiêu chí
          và kế hoạch cải thiện cá nhân hóa.
        </p>
        <Link
          href="/setup"
          className="inline-flex items-center gap-2 bg-[var(--primary)] text-white px-6 py-3 rounded-lg font-medium hover:bg-[var(--primary-hover)] transition-colors text-base shadow-md"
        >
          Bắt đầu Demo →
        </Link>
      </section>

      {/* Workflow Steps */}
      <section>
        <h2 className="text-xl font-semibold mb-5 text-center">Quy trình phỏng vấn</h2>
        <div className="space-y-3">
          {steps.map((s, i) => (
            <div
              key={s.num}
              className="flex items-start gap-4 bg-white border border-[var(--border)] rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-10 h-10 rounded-full bg-[var(--primary)] text-white flex items-center justify-center font-bold text-sm shrink-0">
                {s.num}
              </div>
              <div className="flex-1">
                <h3 className="font-semibold">{s.icon} {s.title}</h3>
                <p className="text-sm text-[var(--muted)]">{s.desc}</p>
              </div>
              {i < steps.length - 1 && (
                <span className="text-gray-300 text-lg mt-1">→</span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* System Status */}
      <section className="bg-white border border-[var(--border)] rounded-xl p-5 shadow-sm">
        <h2 className="font-semibold mb-3">⚙️ Trạng thái hệ thống</h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-[var(--muted)]">Backend URL</span>
            <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">{getBaseUrl()}</code>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[var(--muted)]">Backend Status</span>
            {backendOk === null ? (
              <span className="text-blue-500 animate-pulse text-xs">Đang kiểm tra...</span>
            ) : backendOk ? (
              <span className="text-emerald-600 font-medium text-xs flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Đang chạy
              </span>
            ) : (
              <span className="text-red-600 text-xs">
                ❌ Không kết nối được — chạy <code className="bg-gray-100 px-1 rounded">uvicorn app.main:app --reload</code>
              </span>
            )}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[var(--muted)]">Sample files</span>
            <span className="text-xs text-gray-500">
              <code className="bg-gray-100 px-1 rounded">public/demo_samples/</code>
            </span>
          </div>
        </div>
      </section>

      {/* Tech */}
      <section className="text-center text-sm text-[var(--muted)] pb-6">
        <p>
          Built with <strong>FastAPI</strong> · <strong>Gemini AI</strong> ·{" "}
          <strong>ChromaDB</strong> · <strong>Next.js</strong> · <strong>TypeScript</strong>
        </p>
      </section>
    </div>
  );
}
