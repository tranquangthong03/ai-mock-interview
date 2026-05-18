import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Mock Interviewer",
  description: "Hệ thống luyện phỏng vấn AI - Luyện tập, đánh giá, cải thiện",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen antialiased">
        {/* Top nav */}
        <nav className="border-b border-[var(--border)] bg-white/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
            <Link href="/" className="text-lg font-bold text-[var(--primary)]">
              🎤 AI Mock Interviewer
            </Link>
            <div className="flex gap-4 text-sm text-[var(--muted)]">
              <Link href="/setup" className="hover:text-[var(--foreground)] transition-colors">
                Setup
              </Link>
              <Link href="/setup" className="hover:text-[var(--foreground)] transition-colors">
                Interview
              </Link>
            </div>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
