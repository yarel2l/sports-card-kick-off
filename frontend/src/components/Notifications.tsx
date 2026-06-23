"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { getAccess } from "@/lib/client";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/notifications/";

interface Toast {
  id: number;
  title: string;
  body: string;
}

const ToastCtx = createContext<(t: Omit<Toast, "id">) => void>(() => {});
export const usePushToast = () => useContext(ToastCtx);

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const push = (t: Omit<Toast, "id">) => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 6000);
  };

  // Open the per-user WebSocket while authenticated.
  useEffect(() => {
    if (!user) return;
    const token = getAccess();
    if (!token) return;

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    } catch {
      return;
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as {
          event: string;
          data?: Record<string, unknown>;
        };
        if (msg.event === "alert.triggered") {
          push({
            title: "Price alert triggered",
            body: `A card hit your target (${msg.data?.triggered_price ?? ""}).`,
          });
        } else if (msg.event === "search.status") {
          push({ title: "Search update", body: `Status: ${msg.data?.status}` });
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    return () => {
      ws?.close();
    };
  }, [user]);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="w-72 rounded-lg border border-slate-200 bg-white p-3 shadow-lg"
          >
            <div className="text-sm font-semibold text-slate-900">{t.title}</div>
            <div className="mt-0.5 text-sm text-slate-600">{t.body}</div>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
