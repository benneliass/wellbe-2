"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@wellbe/api-client/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { usePendingItems, useThingsNoticed, useThreads, webQueryKeys } from "./hooks";
import { continuityCounts, LAST_VISIT_KEY, advanceVisit, type ContinuityCounts } from "./home-continuity";
import { useSession } from "./useSession";

type DeltaDigestV2 = components["schemas"]["DeltaDigestV2"];
type ThingNoticedV1 = components["schemas"]["ThingNoticedV1"];

export const homeQueryKeys = {
  delta: (since: string | null) => ["home", "delta", since ?? "default"] as const,
};

export type NoticedAction = "accept" | "reject" | "ignore" | "remind";

export interface NoticedActionInput {
  id: string;
  action: NoticedAction;
  /** Required for "remind": when the card comes back. */
  until?: Date;
}

export interface NoticedActionResult {
  /** Set when accepting opened a new health thread. */
  threadId?: string;
}

/**
 * The four relevance-candidate actions over /v1/things-noticed:
 * accept -> confirm (opens a thread), reject -> dismiss (for good),
 * ignore -> ignore (until noticed again), remind -> snooze (until a date).
 * The card leaves the list immediately; a failed call puts it back.
 */
export function useThingNoticedAction() {
  const qc = useQueryClient();
  return useMutation<NoticedActionResult, Error, NoticedActionInput, { previous?: ThingNoticedV1[] }>({
    mutationFn: async ({ id, action, until }) => {
      const client = getApiClient();
      const path = { params: { path: { candidate_id: id } } };
      if (action === "accept") {
        const { data, error } = await client.POST("/v1/things-noticed/{candidate_id}/confirm", path);
        if (error || !data) throw new Error("Failed to accept");
        return { threadId: data.thread_id };
      }
      if (action === "remind") {
        if (!until) throw new Error("A reminder date is required");
        const { error } = await client.POST("/v1/things-noticed/{candidate_id}/snooze", {
          ...path,
          body: { until: until.toISOString() },
        });
        if (error) throw new Error("Failed to set a reminder");
        return {};
      }
      const { error } =
        action === "reject"
          ? await client.POST("/v1/things-noticed/{candidate_id}/dismiss", path)
          : await client.POST("/v1/things-noticed/{candidate_id}/ignore", path);
      if (error) throw new Error(`Failed to ${action}`);
      return {};
    },
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: webQueryKeys.thingsNoticed });
      const previous = qc.getQueryData<ThingNoticedV1[]>(webQueryKeys.thingsNoticed);
      qc.setQueryData<ThingNoticedV1[]>(webQueryKeys.thingsNoticed, (list) =>
        list?.filter((c) => c.candidate_id !== id),
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(webQueryKeys.thingsNoticed, ctx.previous);
    },
    onSettled: async (_data, _err, { action }) => {
      await qc.invalidateQueries({ queryKey: webQueryKeys.thingsNoticed });
      if (action === "accept") await qc.invalidateQueries({ queryKey: queryKeys.threads });
    },
  });
}

/**
 * Start of the "since you last looked" window, read once per mount from
 * localStorage. `undefined` until resolved; `null` on a first visit.
 */
export function useLastVisitSince(): string | null | undefined {
  const [since, setSince] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    let raw: string | null = null;
    try {
      raw = window.localStorage.getItem(LAST_VISIT_KEY);
    } catch {
      raw = null;
    }
    const { since: start, next } = advanceVisit(raw, new Date());
    try {
      window.localStorage.setItem(LAST_VISIT_KEY, next);
    } catch {
      /* private mode: fall back to the digest's default window */
    }
    setSince(start);
  }, []);
  return since;
}

/** What-changed digest (/v2/delta) since `since`, or the server's default window. */
export function useDelta(since: string | null | undefined) {
  const signedIn = Boolean(useSession()?.patientId);
  return useQuery<DeltaDigestV2>({
    queryKey: homeQueryKeys.delta(since ?? null),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/delta", {
        params: { query: since ? { since } : {} },
      });
      if (error || !data) throw new Error("Failed to load what changed");
      return data;
    },
    enabled: signedIn && since !== undefined,
  });
}

/** Counts for the launcher's continuity strip; null until threads have loaded. */
export function useContinuityCounts(): ContinuityCounts | null {
  const threads = useThreads();
  const pending = usePendingItems();
  const noticed = useThingsNoticed();
  if (!threads.data) return null;
  return continuityCounts(threads.data, pending.data ?? [], noticed.data ?? [], new Date());
}
