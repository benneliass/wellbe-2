"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@wellbe/api-client/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { toThreadSummary } from "./adapters";
import type { ThreadSummary } from "./types";

type PendingItemV2 = components["schemas"]["PendingItemV2"];

/** Real health threads from /v1/threads, mapped to the UI summary shape. */
export function useThreads() {
  return useQuery<ThreadSummary[]>({
    queryKey: queryKeys.threads,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v1/threads");
      if (error || !data) throw new Error("Failed to load threads");
      return data.map(toThreadSummary);
    },
  });
}

/** Open loops (pending items) from /v2/pending-items — the continuity ledger. */
export function usePendingItems() {
  return useQuery<PendingItemV2[]>({
    queryKey: queryKeys.pendingItems,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/pending-items");
      if (error || !data) throw new Error("Failed to load pending items");
      return data;
    },
  });
}

/** A single thread header from /v1/threads/{id}. */
export function useThread(id: string) {
  return useQuery({
    queryKey: queryKeys.thread(id),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v1/threads/{thread_id}", {
        params: { path: { thread_id: id } },
      });
      if (error || !data) throw new Error("Failed to load thread");
      return data;
    },
    enabled: Boolean(id),
  });
}
