"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { webQueryKeys } from "./hooks";

export type ThreadTimelineV2 = components["schemas"]["ThreadTimelineV2"];
export type TimelineEventV2 = components["schemas"]["TimelineEventV2"];
export type TimelineSourceV2 = components["schemas"]["TimelineSourceV2"];

export const threadKeys = {
  timeline: (id: string) => ["threads", id, "timeline"] as const,
};

/** Status history, chronological events, and resolved sources for one thread. */
export function useThreadTimeline(id: string) {
  return useQuery<ThreadTimelineV2>({
    queryKey: threadKeys.timeline(id),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/threads/{thread_id}/timeline", {
        params: { path: { thread_id: id } },
      });
      if (error || !data) throw new Error("Failed to load thread timeline");
      return data;
    },
    enabled: Boolean(id),
  });
}

export interface ThreadNoteInput {
  text: string;
  /** Stable per open sheet so a retry never stores the note twice. */
  idempotencyKey: string;
}

/** Store a note in the user's own words, attached to this thread. */
export function useCaptureToThread(threadId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ text, idempotencyKey }: ThreadNoteInput) => {
      const { data, error } = await getApiClient().POST("/v1/capture", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: {
          schema_version: "c13.capture.request.v1",
          capture_type: "note",
          payload: { text },
          thread_id: threadId,
        },
      });
      if (error || !data) throw new Error("Your note couldn't be saved. Please try again.");
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: threadKeys.timeline(threadId) });
      void qc.invalidateQueries({ queryKey: webQueryKeys.threadMemories(threadId) });
    },
  });
}
