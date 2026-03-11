import { clsx } from "clsx";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center py-16 px-4 text-center",
        className,
      )}
    >
      <Icon size={40} className="text-[#4b5563] mb-4" />
      <h3 className="text-white font-semibold text-base mb-1">{title}</h3>
      <p className="text-[#6b7280] text-sm max-w-sm">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity hover:opacity-80"
          style={{ background: "var(--cta)" }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
