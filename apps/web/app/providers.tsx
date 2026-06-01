"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@wellbe/api-client/react-query";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => createQueryClient());
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
