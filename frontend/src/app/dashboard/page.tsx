"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { cardTitle, formatMoney } from "@/lib/format";
import {
  type Holding,
  type PortfolioSummary,
  type PriceAlert,
  type WatchlistItem,
  getSummary,
  listAlerts,
  listHoldings,
  listWatchlist,
  removeAlert,
  removeHolding,
  removeWatch,
} from "@/lib/portfolio-api";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [watch, setWatch] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [s, h, w, a] = await Promise.all([
        getSummary(),
        listHoldings(),
        listWatchlist(),
        listAlerts(),
      ]);
      setSummary(s);
      setHoldings(h);
      setWatch(w);
      setAlerts(a);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    void reload();
  }, [user, loading, router, reload]);

  if (loading || !user) return <p className="text-slate-500">Loading…</p>;

  const totals = summary?.totals;

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold">Your portfolio</h1>
        <p className="text-slate-500">{user.email}</p>
      </div>

      {err && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>
      )}

      {totals && (
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Holdings" value={String(totals.holdings_count)} />
          <Stat label="Cost basis" value={formatMoney(totals.total_cost)} />
          <Stat label="Market value" value={formatMoney(totals.total_market_value)} />
          <Stat
            label="Unrealized P&L"
            value={formatMoney(totals.total_unrealized_pl)}
          />
        </section>
      )}

      <Section title="Holdings">
        {holdings.length === 0 ? (
          <Empty>No holdings yet. Add one from a card page.</Empty>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {holdings.map((h) => (
              <li key={h.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <Link href={`/cards/${h.card}`} className="hover:text-indigo-700">
                  {cardTitle(h.card_detail)}{" "}
                  <span className="text-slate-400">
                    ×{h.quantity} @ {formatMoney(h.cost_basis)}
                  </span>
                </Link>
                <RemoveButton
                  onClick={async () => {
                    await removeHolding(h.id);
                    void reload();
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Watchlist">
        {watch.length === 0 ? (
          <Empty>Not watching any cards yet.</Empty>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {watch.map((w) => (
              <li key={w.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <Link href={`/cards/${w.card}`} className="hover:text-indigo-700">
                  {cardTitle(w.card_detail)}
                </Link>
                <RemoveButton
                  onClick={async () => {
                    await removeWatch(w.id);
                    void reload();
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Price alerts">
        {alerts.length === 0 ? (
          <Empty>No alerts set.</Empty>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {alerts.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span>
                  <Link href={`/cards/${a.card}`} className="hover:text-indigo-700">
                    {cardTitle(a.card_detail)}
                  </Link>{" "}
                  <span className="text-slate-400">
                    {a.direction === "BELOW" ? "≤" : "≥"} {formatMoney(a.threshold_price)}
                    {a.is_active ? "" : " · triggered"}
                  </span>
                </span>
                <RemoveButton
                  onClick={async () => {
                    await removeAlert(a.id);
                    void reload();
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
      {children}
    </p>
  );
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
    >
      Remove
    </button>
  );
}
