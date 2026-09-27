"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@wellbe/api-client/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { reconcileOidcSession } from "@/lib/auth";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => createQueryClient());
  useEffect(() => {
    void reconcileOidcSession();
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
