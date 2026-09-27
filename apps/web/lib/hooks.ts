"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@wellbe/api-client/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { toThreadSummary } from "./adapters";
import type { ThreadSummary } from "./types";

type PendingItemV2 = components["schemas"]["PendingItemV2"];
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
