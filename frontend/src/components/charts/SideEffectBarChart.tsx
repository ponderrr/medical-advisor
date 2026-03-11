"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from "recharts";
import type { SideEffect } from "@/types/api";

const SEVERITY_COLORS: Record<string, string> = {
  mild:     "#4CA9EF",
  moderate: "#E87722",
  severe:   "#ef4444",
  unknown:  "#6b7280",
};

interface Props {
  data: SideEffect[];
}

export function SideEffectBarChart({ data }: Props) {
  const sorted = [...data]
    .sort((a, b) => b.frequency - a.frequency)
    .slice(0, 10);

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-[#6b7280] text-sm">
        No side effect data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
      >
        <XAxis
          type="number"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="effect"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={120}
        />
        <Tooltip
          contentStyle={{
            background: "#1a1a1f",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 6,
            color: "#fff",
            fontSize: 12,
          }}
          formatter={(value, _name, entry) => [
            `${value} mentions`,
            `Severity: ${entry.payload.severity ?? "unknown"}`,
          ]}
        />
        <Bar dataKey="frequency" radius={[0, 4, 4, 0]}>
          {sorted.map((entry) => (
            <Cell
              key={entry.id}
              fill={SEVERITY_COLORS[entry.severity ?? "unknown"] ?? "#6b7280"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
