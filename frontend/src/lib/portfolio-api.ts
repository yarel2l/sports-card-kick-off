import type { Card, Money } from "./types";
import { apiGet, apiSend, type Paginated } from "./client";

export interface WatchlistItem {
  id: string;
  card: string;
  card_detail: Card;
  created_at: string;
}

export interface Holding {
  id: string;
  card: string;
  card_detail: Card;
  grading_company: string | null;
  grade: string;
  quantity: number;
  cost_basis: string;
  currency: string;
  acquired_at: string | null;
  notes: string;
}

export interface PriceAlert {
  id: string;
  card: string;
  card_detail: Card;
  grade: string;
  direction: "BELOW" | "ABOVE";
  threshold_price: string;
  is_active: boolean;
  triggered_at: string | null;
  triggered_price: string | null;
  created_at: string;
}

export interface ValuedHolding {
  holding_id: string;
  card_id: string;
  quantity: number;
  grade: string | null;
  cost_basis: Money;
  total_cost: Money;
  market_unit_price: Money;
  market_value: Money;
  unrealized_pl: Money;
  currency: string;
}

export interface PortfolioSummary {
  holdings: ValuedHolding[];
  totals: {
    holdings_count: number;
    total_cost: Money;
    total_market_value: Money;
    total_unrealized_pl: Money;
  };
}

// --- Watchlist ---
export const listWatchlist = () =>
  apiGet<Paginated<WatchlistItem>>("/portfolio/watchlist/").then((r) => r.results);
export const addWatch = (cardId: string) =>
  apiSend<WatchlistItem>("/portfolio/watchlist/", "POST", { card: cardId });
export const removeWatch = (id: string) =>
  apiSend<void>(`/portfolio/watchlist/${id}/`, "DELETE");

// --- Holdings ---
export const listHoldings = () =>
  apiGet<Paginated<Holding>>("/portfolio/holdings/").then((r) => r.results);
export const addHolding = (body: {
  card: string;
  quantity: number;
  cost_basis: string;
  grade?: string;
}) => apiSend<Holding>("/portfolio/holdings/", "POST", body);
export const removeHolding = (id: string) =>
  apiSend<void>(`/portfolio/holdings/${id}/`, "DELETE");
export const getSummary = () => apiGet<PortfolioSummary>("/portfolio/summary/");

// --- Alerts ---
export const listAlerts = () =>
  apiGet<Paginated<PriceAlert>>("/portfolio/alerts/").then((r) => r.results);
export const addAlert = (body: {
  card: string;
  direction: "BELOW" | "ABOVE";
  threshold_price: string;
  grade?: string;
}) => apiSend<PriceAlert>("/portfolio/alerts/", "POST", body);
export const removeAlert = (id: string) =>
  apiSend<void>(`/portfolio/alerts/${id}/`, "DELETE");
