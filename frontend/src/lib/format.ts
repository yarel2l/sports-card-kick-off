import type { Card, Money } from "./types";

export function toNum(value: Money): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatMoney(value: Money, currency = "USD"): string {
  const n = toNum(value);
  if (n === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: n >= 1000 ? 0 : 2,
  }).format(n);
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Human-readable card title used for headings and SEO. */
export function cardTitle(card: Card): string {
  const parts: string[] = [];
  if (card.card_set) parts.push(card.card_set.display_name);
  if (card.player) parts.push(card.player.name);
  if (card.card_number) parts.push(`#${card.card_number}`);
  if (card.parallel) parts.push(card.parallel);
  const tail: string[] = [];
  if (card.is_rookie) tail.push("RC");
  if (card.is_autograph) tail.push("Auto");
  return [parts.join(" "), tail.join(" ")].filter(Boolean).join(" · ");
}
