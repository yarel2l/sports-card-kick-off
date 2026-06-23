"use client";

import { AuthProvider } from "./AuthProvider";
import { NotificationsProvider } from "./Notifications";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <NotificationsProvider>{children}</NotificationsProvider>
    </AuthProvider>
  );
}
