"use client";

import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ZAxis,
} from "recharts";
import type { DosingProtocol } from "@/types/api";

const SOURCE_COLORS: Record<string, string> = {
  paper:  "#0047BB",
  reddit: "#E87722",
  tweet:  "#4CA9EF",
  trial:  "#a855f7",
};

const CONF_VALUE: Record<string, number> = { high: 0.9, medium: 0.5, low: 0.1 };

function parseDose(dose: string | null): number | null {
  if (!dose) return null;
  const m = dose.match(/(\d+(?:\.\d+)?)/);
  return m ? parseFloat(m[1]) : null;
}

interface Props {
  data: DosingProtocol[];
}

export function DosingDistributionChart({ data }: Props) {
  const points = data
    .map((d) => ({
      x: parseDose(d.dose),
      y: CONF_VALUE[d.confidence ?? "low"] ?? 0.1,
      source: d.source_type,
      dose: d.dose,
      frequency: d.frequency,
      id: d.id,
    }))
    .filter((p) => p.x !== null);

  if (points.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-[#6b7280] text-sm">
        No dosing data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <XAxis
          type="number"
          dataKey="x"
          name="Dose (mg)"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          label={{ value: "Dose (mg)", position: "insideBottom", offset: -2, fill: "#6b7280", fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Confidence"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          domain={[0, 1]}
          ticks={[0.1, 0.5, 0.9]}
          tickFormatter={(v) => v === 0.9 ? "High" : v === 0.5 ? "Med" : "Low"}
        />
        <ZAxis range={[60, 60]} />
        <Tooltip
          cursor={{ strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.1)" }}
          contentStyle={{
            background: "#1a1a1f",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 6,
            color: "#fff",
            fontSize: 12,
          }}
          formatter={(_value, name, props) => {
            if (name === "Dose (mg)") return [`${props.payload.dose}`, "Dose"];
            if (name === "Confidence") return [props.payload.source, "Source"];
            return [_value, name];
          }}
        />
        {Object.keys(SOURCE_COLORS).map((src) => (
          <Scatter
            key={src}
            name={src}
            data={points.filter((p) => p.source === src)}
            fill={SOURCE_COLORS[src]}
            fillOpacity={0.8}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}
