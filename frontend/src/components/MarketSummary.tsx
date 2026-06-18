import type { MarketSummary } from "@/lib/types";
import { formatMoney } from "@/lib/format";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-900">{value}</div>
    </div>
  );
}

export default function MarketSummaryCard({ market }: { market: MarketSummary }) {
  const c = market.currency;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Stat label="Last" value={formatMoney(market.last, c)} />
      <Stat label="Average" value={formatMoney(market.avg, c)} />
      <Stat label="Median" value={formatMoney(market.median, c)} />
      <Stat label="Min" value={formatMoney(market.min, c)} />
      <Stat label="Max" value={formatMoney(market.max, c)} />
      <Stat label="Comps" value={String(market.count)} />
    </div>
  );
}
