import type { PriceObservation } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/format";
import { KindBadge, SourceBadge } from "./Badges";

export default function CompsTable({ comps }: { comps: PriceObservation[] }) {
  if (comps.length === 0) {
    return (
      <p className="rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        No recent comps yet for this card.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2.5 font-medium">Price</th>
            <th className="px-4 py-2.5 font-medium">Grade</th>
            <th className="px-4 py-2.5 font-medium">Type</th>
            <th className="px-4 py-2.5 font-medium">Source</th>
            <th className="px-4 py-2.5 font-medium">Date</th>
            <th className="px-4 py-2.5 font-medium"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {comps.map((c) => (
            <tr key={c.id} className="hover:bg-slate-50">
              <td className="px-4 py-2.5 font-medium text-slate-900">
                {formatMoney(c.price, c.currency)}
              </td>
              <td className="px-4 py-2.5 text-slate-600">
                {c.grading_company && c.grade ? `${c.grading_company} ${c.grade}` : "Raw"}
              </td>
              <td className="px-4 py-2.5">
                <KindBadge kind={c.kind} />
              </td>
              <td className="px-4 py-2.5">
                <SourceBadge source={c.source} />
              </td>
              <td className="px-4 py-2.5 text-slate-500">{formatDate(c.observed_at)}</td>
              <td className="px-4 py-2.5 text-right">
                {c.url && (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-indigo-600 hover:underline"
                  >
                    View
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
