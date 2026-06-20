"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { usePushToast } from "./Notifications";
import { addAlert, addHolding, addWatch } from "@/lib/portfolio-api";

export default function CardActions({ cardId }: { cardId: string }) {
  const { user } = useAuth();
  const toast = usePushToast();
  const [busy, setBusy] = useState(false);
  const [threshold, setThreshold] = useState("");
  const [direction, setDirection] = useState<"BELOW" | "ABOVE">("BELOW");
  const [qty, setQty] = useState("1");
  const [cost, setCost] = useState("");

  if (!user) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <Link href="/login" className="font-medium text-indigo-600 hover:underline">
          Log in
        </Link>{" "}
        to track this card, set price alerts and add it to your portfolio.
      </div>
    );
  }

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      toast({ title: "Done", body: ok });
    } catch (e) {
      toast({ title: "Error", body: e instanceof Error ? e.message : "Failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-700">Watchlist</h3>
        <button
          disabled={busy}
          onClick={() => run(() => addWatch(cardId), "Added to watchlist")}
          className="mt-2 w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Add to watchlist
        </button>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-700">Price alert</h3>
        <div className="mt-2 flex gap-2">
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as "BELOW" | "ABOVE")}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
          >
            <option value="BELOW">≤</option>
            <option value="ABOVE">≥</option>
          </select>
          <input
            inputMode="decimal"
            placeholder="Price"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          />
        </div>
        <button
          disabled={busy || !threshold}
          onClick={() =>
            run(
              () => addAlert({ card: cardId, direction, threshold_price: threshold }),
              "Alert created",
            )
          }
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          Create alert
        </button>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-700">Add holding</h3>
        <div className="mt-2 flex gap-2">
          <input
            inputMode="numeric"
            placeholder="Qty"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-16 rounded-lg border border-slate-300 px-2 py-2 text-sm"
          />
          <input
            inputMode="decimal"
            placeholder="Cost each"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
          />
        </div>
        <button
          disabled={busy || !cost}
          onClick={() =>
            run(
              () =>
                addHolding({
                  card: cardId,
                  quantity: Number(qty) || 1,
                  cost_basis: cost,
                }),
              "Added to portfolio",
            )
          }
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          Add holding
        </button>
      </div>
    </div>
  );
}
