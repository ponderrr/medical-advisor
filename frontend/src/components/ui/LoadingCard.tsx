import { Skeleton } from "@/components/ui/skeleton";

export function LoadingCard() {
  return (
    <div
      className="rounded-lg p-4 border"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <Skeleton className="h-3 w-20 mb-3 bg-white/5" />
      <Skeleton className="h-7 w-16 mb-2 bg-white/8" />
      <Skeleton className="h-3 w-28 bg-white/4" />
    </div>
  );
}

export function LoadingGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <LoadingCard key={i} />
      ))}
    </div>
  );
}
