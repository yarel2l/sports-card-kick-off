import Link from "next/link";
import type { SearchResultItem } from "@/lib/types";
import { cardTitle, formatMoney } from "@/lib/format";
import { Tag } from "./Badges";

export default function CardResultCard({ item }: { item: SearchResultItem }) {
  const { card, market } = item;
  const value = market.last ?? market.avg;

  return (
    <Link
      href={`/cards/${card.id}`}
      className="group flex flex-col rounded-xl border border-slate-200 bg-white p-4 transition hover:border-slate-400 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-medium leading-snug text-slate-900 group-hover:text-indigo-700">
          {cardTitle(card)}
        </h3>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {card.player?.sport && <Tag>{card.player.sport}</Tag>}
        {card.is_rookie && <Tag>RC</Tag>}
        {card.is_autograph && <Tag>Auto</Tag>}
        {card.serial_limit && <Tag>/{card.serial_limit}</Tag>}
      </div>

      <div className="mt-4 flex items-end justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">
            {market.last != null ? "Last sale" : "Avg value"}
          </div>
          <div className="text-xl font-semibold text-slate-900">
            {formatMoney(value, market.currency)}
          </div>
        </div>
        <div className="text-right text-xs text-slate-500">
          {market.count} comp{market.count === 1 ? "" : "s"}
        </div>
      </div>
    </Link>
  );
}
