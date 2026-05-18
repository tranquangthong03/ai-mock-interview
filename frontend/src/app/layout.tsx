import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Mock Interviewer",
  description:
    "Practice English technical interviews with AI questions, voice answers, Vietnamese feedback, and detailed reports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <AppNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
