import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import MarketSummaryCard from "@/components/MarketSummary";
import CompsTable from "@/components/CompsTable";
import CardActions from "@/components/CardActions";
import PriceHistoryChart from "@/components/PriceHistoryChart";
import { getCardHistory, getCardPrices } from "@/lib/api";
import { cardTitle, formatMoney } from "@/lib/format";
import type { CardPricesResponse } from "@/lib/types";

type Params = Promise<{ id: string }>;
type Search = Promise<{ interval?: string }>;

const INTERVALS = ["day", "week", "month"] as const;
type Interval = (typeof INTERVALS)[number];

async function loadPrices(id: string): Promise<CardPricesResponse | null> {
  try {
    return await getCardPrices(id);
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { id } = await params;
  const data = await loadPrices(id);
  if (!data) return { title: "Card not found" };

  const title = cardTitle(data.card);
  const value = formatMoney(
    data.market.overall.last ?? data.market.overall.avg,
    data.market.overall.currency,
  );
  return {
    title,
    description: `${title} — market value ${value} from ${data.market.overall.count} aggregated comps across eBay, 130Point, COMC and Goldin. View price history and recent sales.`,
  };
}

export default async function CardPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: Search;
}) {
  const { id } = await params;
  const { interval: rawInterval } = await searchParams;
  const interval: Interval = INTERVALS.includes(rawInterval as Interval)
    ? (rawInterval as Interval)
    : "week";

  const data = await loadPrices(id);
  if (!data) notFound();

  const history = await getCardHistory(id, interval).catch(() => null);
  const { card, market, recent_observations } = data;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/search" className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to search
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 sm:text-3xl">
          {cardTitle(card)}
        </h1>
        {card.card_set && (
          <p className="mt-1 text-slate-500">
            {card.card_set.brand} · {card.card_set.year} · {card.player?.sport}
          </p>
        )}
      </div>

      <CardActions cardId={card.id} />

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Market value
        </h2>
        <MarketSummaryCard market={market.overall} />
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Price history
          </h2>
          <div className="flex gap-1 text-xs">
            {INTERVALS.map((iv) => (
              <Link
                key={iv}
                href={`/cards/${id}?interval=${iv}`}
                className={`rounded-md px-2.5 py-1 capitalize ${
                  iv === interval
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
                }`}
              >
                {iv}
              </Link>
            ))}
          </div>
        </div>
        {history ? (
          <PriceHistoryChart history={history.history} />
        ) : (
          <p className="text-sm text-slate-500">Price history unavailable.</p>
        )}
      </section>

      {market.by_grade.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            By grade
          </h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Grade</th>
                  <th className="px-4 py-2.5 font-medium">Avg</th>
                  <th className="px-4 py-2.5 font-medium">Min</th>
                  <th className="px-4 py-2.5 font-medium">Max</th>
                  <th className="px-4 py-2.5 font-medium">Comps</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {market.by_grade.map((g, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-medium text-slate-900">
                      {g.grading_company && g.grade
                        ? `${g.grading_company} ${g.grade}`
                        : "Raw"}
                    </td>
                    <td className="px-4 py-2.5">{formatMoney(g.avg)}</td>
                    <td className="px-4 py-2.5">{formatMoney(g.min)}</td>
                    <td className="px-4 py-2.5">{formatMoney(g.max)}</td>
                    <td className="px-4 py-2.5 text-slate-500">{g.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Recent comps
        </h2>
        <CompsTable comps={recent_observations} />
      </section>
    </div>
  );
}
