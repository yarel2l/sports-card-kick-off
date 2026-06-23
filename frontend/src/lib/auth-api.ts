import { API_BASE, apiGet, clearTokens, setTokens } from "./client";

export interface AuthUser {
  account_id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
}

interface LoginResponse {
  user: AuthUser;
  tokens: { access: string; refresh: string };
}

async function postPublic<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const fromValues = Object.values(detail).flat().filter(Boolean).join(" ");
    const msg =
      (typeof detail.detail === "string" && detail.detail) ||
      fromValues ||
      `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return (await res.json()) as T;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const data = await postPublic<LoginResponse>("/auth/login/", { email, password });
  setTokens(data.tokens.access, data.tokens.refresh);
  return data.user;
}

export async function register(payload: {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
}): Promise<AuthUser> {
  const data = await postPublic<LoginResponse>("/auth/register/", payload);
  setTokens(data.tokens.access, data.tokens.refresh);
  return data.user;
}

export function getMe(): Promise<AuthUser> {
  return apiGet<AuthUser>("/auth/me/");
}

export function logout() {
  clearTokens();
}
