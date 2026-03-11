"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const RECEPTOR_COLORS: Record<string, string> = {
  "GLP-1R": "#0047BB",
  "GIPR":   "#4CA9EF",
  "GcgR":   "#E87722",
  "Other":  "#6b7280",
};

function getColor(receptor: string): string {
  return RECEPTOR_COLORS[receptor] ?? RECEPTOR_COLORS.Other;
}

interface Props {
  data: Array<{ receptor: string; count: number }>;
  totalMechanisms: number;
}

export function ReceptorCoverageChart({ data, totalMechanisms }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-[#6b7280] text-sm">
        No mechanism data
      </div>
    );
  }

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="receptor"
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={100}
            paddingAngle={3}
          >
            {data.map((entry) => (
              <Cell key={entry.receptor} fill={getColor(entry.receptor)} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#1a1a1f",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 6,
              color: "#fff",
              fontSize: 12,
            }}
          />
          <Legend
            formatter={(value) => (
              <span style={{ color: "#9ca3af", fontSize: 12 }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      {/* Center label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <p className="text-2xl font-bold text-white">{totalMechanisms}</p>
        <p className="text-[10px] text-[#6b7280] uppercase tracking-wider">Mechanisms</p>
      </div>
    </div>
  );
}
