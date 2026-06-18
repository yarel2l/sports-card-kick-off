import type { Metadata } from "next";
import SearchBar from "@/components/SearchBar";
import InterpretedQueryChips from "@/components/InterpretedQuery";
import CardResultCard from "@/components/CardResultCard";
import { searchCards } from "@/lib/api";

export const metadata: Metadata = {
  title: "Search cards",
};

type SearchParams = Promise<{ q?: string; grade?: string; grading_company?: string }>;

export default async function SearchPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { q = "", grade, grading_company } = await searchParams;

  let error = false;
  let data = null;
  if (q.trim()) {
    try {
      data = await searchCards({ q, grade, grading_company });
    } catch {
      error = true;
    }
  }

  return (
    <div className="space-y-6">
      <SearchBar initialValue={q} />

      {!q.trim() && (
        <p className="text-slate-500">Type a query above to search the catalog.</p>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Couldn&apos;t reach the catalog API. Is the backend running at{" "}
          <code>{process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}</code>?
        </div>
      )}

      {data && (
        <>
          <div className="flex flex-col gap-2">
            <p className="text-sm text-slate-500">
              {data.count} result{data.count === 1 ? "" : "s"} for{" "}
              <span className="font-medium text-slate-700">{q}</span>
            </p>
            <InterpretedQueryChips q={data.interpreted_query} />
          </div>

          {data.results.length === 0 ? (
            <p className="rounded-lg bg-white px-4 py-10 text-center text-slate-500 ring-1 ring-slate-200">
              No cards matched. The catalog grows as searches are ingested — try a
              broader query.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.results.map((item) => (
                <CardResultCard key={item.card.id} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
