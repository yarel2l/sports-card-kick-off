// Thin server-side API client for the public catalog endpoints.

import type {
  CardHistoryResponse,
  CardPricesResponse,
  CatalogSearchResponse,
  FeedObservation,
  SearchResultItem,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // Pricing data is time-sensitive; always fetch fresh on the server.
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} for ${path}`);
  }
  return (await res.json()) as T;
}

export function searchCards(params: {
  q?: string;
  grade?: string;
  grading_company?: string;
  limit?: number;
  offset?: number;
}): Promise<CatalogSearchResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.grade) qs.set("grade", params.grade);
  if (params.grading_company) qs.set("grading_company", params.grading_company);
  qs.set("limit", String(params.limit ?? 24));
  if (params.offset) qs.set("offset", String(params.offset));
  return getJSON<CatalogSearchResponse>(`/catalog/search/?${qs.toString()}`);
}

export function getCardPrices(
  id: string,
  params: { grade?: string; grading_company?: string } = {},
): Promise<CardPricesResponse> {
  const qs = new URLSearchParams();
  if (params.grade) qs.set("grade", params.grade);
  if (params.grading_company) qs.set("grading_company", params.grading_company);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return getJSON<CardPricesResponse>(`/catalog/cards/${id}/prices/${suffix}`);
}

export function getCardHistory(
  id: string,
  interval: "day" | "week" | "month" = "week",
): Promise<CardHistoryResponse> {
  return getJSON<CardHistoryResponse>(
    `/catalog/cards/${id}/history/?interval=${interval}`,
  );
}

export function getTrending(
  limit = 8,
): Promise<{ count: number; results: SearchResultItem[] }> {
  return getJSON(`/catalog/trending/?limit=${limit}`);
}

export function getFeed(
  limit = 10,
): Promise<{ count: number; results: FeedObservation[] }> {
  return getJSON(`/catalog/feed/?limit=${limit}`);
}
