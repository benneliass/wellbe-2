"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";

export type InvestigationV2 = components["schemas"]["InvestigationV2"];
export type TheoryV2 = components["schemas"]["TheoryV2"];
export type TheoryEvaluationV2 = components["schemas"]["TheoryEvaluationV2"];
export type TheoryAssessment = components["schemas"]["TheoryAssessment"];
export type EvidenceRefRequest = components["schemas"]["EvidenceRefRequest"];
type MemoryEntryV2 = components["schemas"]["MemoryEntryV2"];

export const theoryKeys = {
  investigations: ["investigations"] as const,
  theories: (investigationId: string) => ["investigations", investigationId, "theories"] as const,
  evaluations: (theoryId: string) => ["theories", theoryId, "evaluations"] as const,
  memories: (threadId: string) => ["threads", threadId, "memories"] as const,
};

/** A piece of the thread's own evidence the user can cite when evaluating. */
export interface EvidenceOption {
  kind: EvidenceRefRequest["kind"];
  id: string;
  label: string;
}

/** Investigations that include this thread. */
export function useThreadInvestigations(threadId: string) {
  return useQuery<InvestigationV2[]>({
    queryKey: theoryKeys.investigations,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/investigations");
      if (error || !data) throw new Error("Failed to load investigations");
      return data;
    },
    select: (all) => all.filter((i) => i.health_thread_ids.includes(threadId)),
    enabled: Boolean(threadId),
  });
}

export function useInvestigationTheories(investigationId: string) {
  return useQuery<TheoryV2[]>({
    queryKey: theoryKeys.theories(investigationId),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET(
        "/v2/investigations/{investigation_id}/theories",
        { params: { path: { investigation_id: investigationId } } },
      );
      if (error || !data) throw new Error("Failed to load theories");
      return data;
    },
  });
}

export function useTheoryEvaluations(theoryId: string, enabled: boolean) {
  return useQuery<TheoryEvaluationV2[]>({
    queryKey: theoryKeys.evaluations(theoryId),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/theories/{theory_id}/evaluations", {
        params: { path: { theory_id: theoryId } },
      });
      if (error || !data) throw new Error("Failed to load evaluations");
      return data;
    },
    enabled,
  });
}

/** The thread's citable evidence: C4 facts referenced by its memories. */
export function useThreadEvidenceOptions(threadId: string) {
  return useQuery<MemoryEntryV2[], Error, EvidenceOption[]>({
    queryKey: theoryKeys.memories(threadId),
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/threads/{thread_id}/memories", {
        params: { path: { thread_id: threadId } },
      });
      if (error || !data) throw new Error("Failed to load thread evidence");
      return data;
    },
    select: (memories) => {
      const seen = new Map<string, EvidenceOption>();
      for (const m of memories) {
        for (const ref of m.source_refs ?? []) {
          const id = ref["source_ref_id"];
          if (ref["source_ref_type"] !== "c4_extracted_fact" || typeof id !== "string") continue;
          if (!seen.has(id)) seen.set(id, { kind: "fact", id, label: m.title || "Untitled entry" });
        }
      }
      return [...seen.values()];
    },
    enabled: Boolean(threadId),
  });
}

/** An evaluation the server refused, with its stable problem code. */
export class EvaluationProblem extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | undefined,
  ) {
    super(message);
  }
}

function problemFrom(error: unknown, status: number): EvaluationProblem {
  const body = (error ?? {}) as { detail?: unknown; code?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "Couldn't save your evaluation.";
  const code = typeof body.code === "string" ? body.code : undefined;
  return new EvaluationProblem(detail, status, code);
}

export interface EvaluateInput {
  theoryId: string;
  investigationId: string;
  toStatus: TheoryAssessment;
  rationale: string;
  evidenceRefs: EvidenceRefRequest[];
  expectedVersion: number;
  /** Stable per form, so a retry after a failure can never record twice. */
  idempotencyKey: string;
}

export function useEvaluateTheory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: EvaluateInput) => {
      const { data, error, response } = await getApiClient().POST(
        "/v2/theories/{theory_id}/evaluate",
        {
          params: {
            path: { theory_id: input.theoryId },
            header: { "Idempotency-Key": input.idempotencyKey },
          },
          body: {
            to_status: input.toStatus,
            rationale: input.rationale,
            evidence_refs: input.evidenceRefs,
            expected_version: input.expectedVersion,
          },
        },
      );
      if (error || !data) throw problemFrom(error, response?.status ?? 0);
      return data;
    },
    onSettled: (_data, _error, input) => {
      void queryClient.invalidateQueries({ queryKey: theoryKeys.theories(input.investigationId) });
      void queryClient.invalidateQueries({ queryKey: theoryKeys.evaluations(input.theoryId) });
    },
  });
}
