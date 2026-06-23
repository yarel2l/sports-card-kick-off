// Types mirroring the Sports Card Kickoff DRF API (catalog endpoints).
// Money fields can arrive as number or string depending on the endpoint, so
// they are typed loosely and normalized via `toNum` in lib/format.

export type Money = number | string | null;

export interface Player {
  id: string;
  name: string;
  slug: string;
  sport: string;
  aliases: string[];
}

export interface CardSet {
  id: string;
  year: number;
  brand: string;
  name: string;
  sport: string;
  slug: string;
  display_name: string;
}

export interface Card {
  id: string;
  canonical_key: string;
  card_set: CardSet | null;
  player: Player | null;
  card_number: string;
  parallel: string;
  is_rookie: boolean;
  is_autograph: boolean;
  is_memorabilia: boolean;
  serial_limit: number | null;
  attributes: Record<string, unknown>;
}

export interface MarketSummary {
  count: number;
  min: Money;
  max: Money;
  avg: Money;
  median: Money;
  last: Money;
  last_observed_at: string | null;
  currency: string;
}

export interface SearchResultItem {
  card: Card;
  market: MarketSummary;
}

export interface InterpretedQuery {
  player_name: string | null;
  year: number | null;
  brand: string | null;
  set_name: string | null;
  parallel: string | null;
  card_number: string | null;
  grading_company: string | null;
  grade: string | null;
  is_rookie: boolean;
}

export interface CatalogSearchResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SearchResultItem[];
  interpreted_query: InterpretedQuery;
}

export interface GradeBreakdown {
  grading_company: string | null;
  grade: string | null;
  count: number;
  min: Money;
  max: Money;
  avg: Money;
}

export interface PriceObservation {
  id: string;
  card: string;
  source: string;
  kind: "LISTING" | "SOLD" | "AUCTION" | string;
  grading_company: string | null;
  grade: string;
  price: Money;
  currency: string;
  url: string;
  match_confidence: number;
  observed_at: string;
}

export interface CardPricesResponse {
  card: Card;
  market: { overall: MarketSummary; by_grade: GradeBreakdown[] };
  recent_observations: PriceObservation[];
}

export interface HistoryPoint {
  bucket: string;
  avg: Money;
  min: Money;
  max: Money;
  count: number;
}

export interface CardHistoryResponse {
  card_id: string;
  interval: string;
  history: HistoryPoint[];
}

export interface FeedObservation {
  id: string;
  card: Card;
  source: string;
  kind: "LISTING" | "SOLD" | "AUCTION" | string;
  grading_company: string | null;
  grade: string;
  price: Money;
  currency: string;
  url: string;
  observed_at: string;
}
