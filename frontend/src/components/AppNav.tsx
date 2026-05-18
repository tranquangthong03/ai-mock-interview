"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/api";
import { cn } from "@/components/ui";

const links = [
  { href: "/", label: "Home", activePath: "/" },
  { href: "/setup", label: "Setup", activePath: "/setup" },
  { href: "/#workflow", label: "Workflow", activePath: "" },
];

export function AppNav() {
  const pathname = usePathname();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    checkBackendHealth().then(setBackendOk);
  }, []);

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/85 shadow-[0_1px_0_rgba(34,211,238,0.08)] backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between gap-6 px-6 lg:px-8">
        <Link href="/" className="group flex min-w-0 items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-cyan-400/40 bg-slate-900 text-sm font-black text-cyan-300 shadow-lg shadow-cyan-950/40 transition group-hover:border-cyan-300 group-hover:text-cyan-200">
            AI
          </span>
          <span className="min-w-0">
            <span className="block truncate text-base font-bold tracking-tight text-slate-50">
              AI Mock Interviewer
            </span>
            <span className="block truncate text-xs font-medium text-slate-400">
              Technical Interview Platform
            </span>
          </span>
        </Link>

        <div className="flex items-center gap-2 text-sm font-semibold">
          {links.map((link) => {
            const active = link.activePath ? (link.activePath === "/" ? pathname === "/" : pathname.startsWith(link.activePath)) : false;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-xl border border-transparent px-4 py-2 text-slate-300 transition hover:border-slate-700 hover:bg-slate-800/80 hover:text-white",
                  active && "border-cyan-500/30 bg-slate-800 text-cyan-200 shadow-sm shadow-cyan-950/30"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs font-semibold text-slate-300">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              backendOk === null && "animate-pulse bg-cyan-300",
              backendOk === true && "bg-emerald-400",
              backendOk === false && "bg-rose-400"
            )}
          />
          {backendOk === null ? "Checking backend" : backendOk ? "Backend Online" : "Backend Offline"}
        </div>
      </div>
    </nav>
  );
}
