"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SearchBar({
  initialValue = "",
  autoFocus = false,
}: {
  initialValue?: string;
  autoFocus?: boolean;
}) {
  const router = useRouter();
  const [value, setValue] = useState(initialValue);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
  }

  return (
    <form onSubmit={submit} className="w-full">
      <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 shadow-sm focus-within:border-slate-500 focus-within:ring-2 focus-within:ring-slate-200">
        <svg
          className="h-5 w-5 shrink-0 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
        </svg>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoFocus={autoFocus}
          placeholder="e.g. 2018 Prizm Luka Doncic #280 PSA 10"
          className="w-full bg-transparent text-slate-900 placeholder:text-slate-400 focus:outline-none"
          aria-label="Search cards"
        />
        <button
          type="submit"
          className="shrink-0 rounded-lg bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Search
        </button>
      </div>
    </form>
  );
}
