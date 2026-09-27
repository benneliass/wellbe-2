"use client";

import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@wellbe/api-client/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { toThreadSummary } from "./adapters";
import type { ThreadSummary } from "./types";

type PendingItemV2 = components["schemas"]["PendingItemV2"];
type ThingNoticedV1 = components["schemas"]["ThingNoticedV1"];
type MemoryEntryV2 = components["schemas"]["MemoryEntryV2"];
type ThreadSubgraphV2 = components["schemas"]["ThreadSubgraphV2"];

/** Query keys for surfaces the shared api-client keys don't cover yet. */
export const webQueryKeys = {
  thingsNoticed: ["things-noticed"] as const,
  threadMemories: (id: string) => ["threads", id, "memories"] as const,
  threadGraph: (id: string) => ["threads", id, "graph"] as const,
};

type NotificationListV2 = components["schemas"]["NotificationListV2"];

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

/** "Things noticed" candidates from /v1/things-noticed (pending review first). */
export function useThingsNoticed() {
  return useQuery<ThingNoticedV1[]>({
    queryKey: webQueryKeys.thingsNoticed,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v1/things-noticed");
      if (error || !data) throw new Error("Failed to load things noticed");
      return data;
    },
  });
}

/** Confirm (promote to a thread) or dismiss a thing noticed, then refresh. */
export function useReviewThingNoticed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "confirm" | "dismiss" }) => {
      const params = { params: { path: { candidate_id: id } } };
      const { error } =
        action === "confirm"
          ? await getApiClient().POST("/v1/things-noticed/{candidate_id}/confirm", params)
          : await getApiClient().POST("/v1/things-noticed/{candidate_id}/dismiss", params);
      if (error) throw new Error(`Failed to ${action}`);
    },
    onSuccess: async (_data, { action }) => {
      await qc.invalidateQueries({ queryKey: webQueryKeys.thingsNoticed });
      if (action === "confirm") await qc.invalidateQueries({ queryKey: queryKeys.threads });
    },
  });
}

async function fetchThreadMemories(id: string): Promise<MemoryEntryV2[]> {
  const { data, error } = await getApiClient().GET("/v2/threads/{thread_id}/memories", {
    params: { path: { thread_id: id } },
  });
  if (error || !data) throw new Error("Failed to load memories");
  return data;
}

async function fetchThreadGraph(id: string): Promise<ThreadSubgraphV2> {
  const { data, error } = await getApiClient().GET("/v2/graph/threads/{thread_id}", {
    params: { path: { thread_id: id } },
  });
  if (error || !data) throw new Error("Failed to load graph");
  return data;
}

/** Memory entries kept around one thread (/v2/threads/{id}/memories). */
export function useThreadMemories(id: string) {
  return useQuery({
    queryKey: webQueryKeys.threadMemories(id),
    queryFn: () => fetchThreadMemories(id),
    enabled: Boolean(id),
  });
}

/** One thread's knowledge-graph neighbourhood (/v2/graph/threads/{id}). */
export function useThreadGraph(id: string) {
  return useQuery({
    queryKey: webQueryKeys.threadGraph(id),
    queryFn: () => fetchThreadGraph(id),
    enabled: Boolean(id),
  });
}

/** Per-thread memories for every given thread, fetched in parallel. */
export function useMemoriesForThreads(ids: string[]) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: webQueryKeys.threadMemories(id),
      queryFn: () => fetchThreadMemories(id),
    })),
  });
}

/** Per-thread subgraphs for every given thread, fetched in parallel. */
export function useGraphsForThreads(ids: string[]) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: webQueryKeys.threadGraph(id),
      queryFn: () => fetchThreadGraph(id),
    })),
  });
}

/**
 * In-app notifications (unread first) from /v2/notifications. Polled gently so a
 * follow-up that comes due shows up without a reload — in-app only, never pushed.
 */
export function useNotifications(enabled = true) {
  return useQuery<NotificationListV2>({
    queryKey: queryKeys.notifications,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/notifications", {
        params: { query: { limit: 20 } },
      });
      if (error || !data) throw new Error("Failed to load notifications");
      return data;
    },
    enabled,
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      const { error } = await getApiClient().POST("/v2/notifications/{notification_id}/read", {
        params: { path: { notification_id: notificationId } },
      });
      if (error) throw new Error("Failed to mark notification read");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.notifications }),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error } = await getApiClient().POST("/v2/notifications/read-all");
      if (error) throw new Error("Failed to mark notifications read");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.notifications }),
  });
}
