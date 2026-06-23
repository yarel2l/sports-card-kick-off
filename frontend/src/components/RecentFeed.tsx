import Link from "next/link";
import type { FeedObservation } from "@/lib/types";
import { cardTitle, formatMoney } from "@/lib/format";
import { KindBadge, SourceBadge } from "./Badges";

export default function RecentFeed({ items }: { items: FeedObservation[] }) {
  if (items.length === 0) return null;
  return (
    <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {items.map((o) => (
        <li key={o.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
          <Link href={`/cards/${o.card.id}`} className="truncate hover:text-indigo-700">
            {cardTitle(o.card)}
          </Link>
          <div className="flex shrink-0 items-center gap-2">
            <KindBadge kind={o.kind} />
            <SourceBadge source={o.source} />
            <span className="w-20 text-right font-medium text-slate-900">
              {formatMoney(o.price, o.currency)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
