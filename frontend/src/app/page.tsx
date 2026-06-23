import SearchBar from "@/components/SearchBar";
import CardResultCard from "@/components/CardResultCard";
import RecentFeed from "@/components/RecentFeed";
import { getFeed, getTrending } from "@/lib/api";
import type { FeedObservation, SearchResultItem } from "@/lib/types";

const EXAMPLES = [
  "2018 Prizm Luka Doncic PSA 10",
  "Mike Trout rookie BGS 9.5",
  "Michael Jordan Fleer 1986",
  "Justin Jefferson Optic rookie",
];

export default async function Home() {
  let trending: SearchResultItem[] = [];
  let feed: FeedObservation[] = [];
  try {
    [trending, feed] = await Promise.all([
      getTrending(8).then((r) => r.results),
      getFeed(10).then((r) => r.results),
    ]);
  } catch {
    // Backend may be unavailable; the landing page still renders.
  }

  return (
    <div className="space-y-12">
      <div className="mx-auto max-w-3xl pt-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Find what any card is really worth
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Search real sold comps and market value aggregated from eBay, 130Point,
          COMC and Goldin — with price history and grade-by-grade breakdowns.
        </p>
        <div className="mt-8">
          <SearchBar autoFocus />
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-slate-400">Try:</span>
          {EXAMPLES.map((ex) => (
            <a
              key={ex}
              href={`/search?q=${encodeURIComponent(ex)}`}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-600 hover:border-slate-400 hover:text-slate-900"
            >
              {ex}
            </a>
          ))}
        </div>
      </div>

      {trending.length > 0 && (
        <section>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Trending cards
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {trending.map((item) => (
              <CardResultCard key={item.card.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {feed.length > 0 && (
        <section>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Recent sales
          </h2>
          <RecentFeed items={feed} />
        </section>
      )}
    </div>
  );
}
