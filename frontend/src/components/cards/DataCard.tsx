import { clsx } from "clsx";
import type { LucideIcon } from "lucide-react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface DataCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  icon?: LucideIcon;
  className?: string;
}

export function DataCard({ title, value, subtitle, trend, icon: Icon, className }: DataCardProps) {
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : "text-[#6b7280]";

  return (
    <div
      className={clsx("rounded-lg p-4 border flex flex-col gap-2", className)}
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest text-[#6b7280] font-medium">{title}</p>
        {Icon && <Icon size={16} className="text-[#4b5563]" />}
      </div>
      <p className="text-2xl font-bold text-white leading-none">{value}</p>
      {(subtitle || trend) && (
        <div className="flex items-center gap-1.5">
          {trend && <TrendIcon size={13} className={trendColor} />}
          {subtitle && <p className="text-xs text-[#6b7280]">{subtitle}</p>}
        </div>
      )}
    </div>
  );
}
