/**
 * React Query helpers for the WellBe web app.
 * Imported via the "@wellbe/api-client/react-query" entry so non-React consumers
 * (the plain runtime client) don't pull in @tanstack/react-query.
 */
import { QueryClient } from "@tanstack/react-query";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export const queryKeys = {
  health: ["health"] as const,
  threads: ["threads"] as const,
  thread: (id: string) => ["threads", id] as const,
  pendingItems: ["pending-items"] as const,
};
