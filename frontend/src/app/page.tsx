import SearchBar from "@/components/SearchBar";

const EXAMPLES = [
  "2018 Prizm Luka Doncic PSA 10",
  "Mike Trout rookie BGS 9.5",
  "Michael Jordan Fleer 1986",
  "Justin Jefferson Optic rookie",
];

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl py-12 text-center">
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
  );
}
