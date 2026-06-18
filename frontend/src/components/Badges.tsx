const SOURCE_LABELS: Record<string, string> = {
  ebay: "eBay",
  "130point": "130Point",
  comc: "COMC",
  goldin: "Goldin",
};

const KIND_STYLES: Record<string, string> = {
  SOLD: "bg-emerald-100 text-emerald-800",
  AUCTION: "bg-amber-100 text-amber-800",
  LISTING: "bg-slate-100 text-slate-700",
};

export function SourceBadge({ source }: { source: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
      {SOURCE_LABELS[source] ?? source}
    </span>
  );
}

export function KindBadge({ kind }: { kind: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
        KIND_STYLES[kind] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {kind === "SOLD" ? "Sold" : kind === "AUCTION" ? "Auction" : "Listing"}
    </span>
  );
}

export function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
      {children}
    </span>
  );
}
