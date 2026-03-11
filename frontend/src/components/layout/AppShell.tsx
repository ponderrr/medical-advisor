"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Syringe,
  AlertTriangle,
  Microscope,
  GitMerge,
  MessageSquare,
} from "lucide-react";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/badge";
import { useHealth } from "@/hooks/useHealth";

const NAV_ITEMS = [
  { href: "/",              label: "Overview",     Icon: LayoutDashboard },
  { href: "/dosing",        label: "Dosing",       Icon: Syringe },
  { href: "/side-effects",  label: "Side Effects", Icon: AlertTriangle },
  { href: "/mechanisms",    label: "Mechanisms",   Icon: Microscope },
  { href: "/conflicts",     label: "Conflicts",    Icon: GitMerge },
  { href: "/query",         label: "Query",        Icon: MessageSquare },
];

function NavItem({ href, label, Icon, active }: { href: string; label: string; Icon: React.ElementType; active: boolean }) {
  return (
    <Link
      href={href}
      className={clsx(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
        active
          ? "bg-[#0047BB]/20 text-white"
          : "text-[#9ca3af] hover:text-white hover:bg-white/5",
      )}
    >
      <Icon size={18} className={active ? "text-[#4CA9EF]" : ""} />
      <span className="hidden md:block">{label}</span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const health = useHealth(30_000);

  const synthReady = health?.synthesis_ready ?? false;

  return (
    <div className="flex flex-col min-h-screen md:flex-row" style={{ background: "var(--bg-base)" }}>
      {/* ── Desktop sidebar ── */}
      <aside
        className="hidden md:flex flex-col w-60 shrink-0 border-r h-screen sticky top-0"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        {/* Logo / compound name */}
        <div className="px-4 py-5 border-b" style={{ borderColor: "var(--border)" }}>
          <p className="text-[10px] font-bold tracking-[0.2em] text-[#9ca3af] uppercase">
            Medical Advisor
          </p>
          <p className="text-sm font-bold tracking-[0.15em] text-white uppercase mt-0.5">
            RETATRUTIDE
          </p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 flex flex-col gap-1">
          {NAV_ITEMS.map(({ href, label, Icon }) => (
            <NavItem key={href} href={href} label={label} Icon={Icon} active={pathname === href} />
          ))}
        </nav>

        {/* Synthesis status */}
        <div className="px-4 py-4 border-t" style={{ borderColor: "var(--border)" }}>
          <Badge
            className={clsx(
              "text-xs font-medium px-2.5 py-1 rounded-full",
              synthReady
                ? "bg-emerald-900/40 text-emerald-400 border border-emerald-700/50"
                : "bg-amber-900/40 text-amber-400 border border-amber-700/50",
            )}
          >
            {health === null ? "…" : synthReady ? "Synthesis Ready" : "Run Synthesis"}
          </Badge>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <header
          className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b md:hidden"
          style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
        >
          <p className="text-xs font-bold tracking-[0.15em] text-white uppercase">RETATRUTIDE</p>
          <Badge
            className={clsx(
              "text-xs font-medium px-2 py-0.5",
              synthReady
                ? "bg-emerald-900/40 text-emerald-400"
                : "bg-amber-900/40 text-amber-400",
            )}
          >
            {synthReady ? "Ready" : "Pending"}
          </Badge>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 md:p-6 pb-24 md:pb-6">{children}</main>
      </div>

      {/* ── Mobile bottom tab bar ── */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-20 flex border-t"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        {NAV_ITEMS.map(({ href, label, Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
                active ? "text-[#4CA9EF]" : "text-[#6b7280]",
              )}
            >
              <Icon size={20} />
              <span>{label.split(" ")[0]}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
