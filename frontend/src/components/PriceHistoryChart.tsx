"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryPoint } from "@/lib/types";
import { toNum } from "@/lib/format";

export default function PriceHistoryChart({
  history,
}: {
  history: HistoryPoint[];
}) {
  const data = history
    .map((h) => ({
      date: new Date(h.bucket).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      avg: toNum(h.avg),
    }))
    .filter((d) => d.avg !== null);

  if (data.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
        Not enough data to chart a price history yet.
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#64748b" }} />
          <YAxis
            tick={{ fontSize: 12, fill: "#64748b" }}
            tickFormatter={(v) => `$${v}`}
            width={56}
          />
          <Tooltip
            formatter={(value) => [`$${value ?? ""}`, "Avg"]}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Line
            type="monotone"
            dataKey="avg"
            stroke="#4f46e5"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
