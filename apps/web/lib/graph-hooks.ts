"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { buildLiveGraph } from "@/components/graph/liveGraphAdapter";
import type { GraphModel } from "@/components/graph/graphData";
import { getApiClient } from "./api";
import { useGraphsForThreads, useMemoriesForThreads, usePendingItems, useThreads } from "./hooks";
import { useResults } from "./records-hooks";
import { theoryKeys, type InvestigationV2 } from "./theories";

type PatternsResponseV2 = components["schemas"]["PatternsResponseV2"];

export const graphKeys = {
  patterns: ["patterns"] as const,
};

/** Plain-language, source-linked patterns from /v2/patterns (keyed by edge id). */
export function usePatterns() {
  return useQuery<PatternsResponseV2>({
    queryKey: graphKeys.patterns,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/patterns", { params: { query: {} } });
      if (error || !data) throw new Error("Failed to load patterns");
      return data;
    },
  });
}

/** Every investigation for the person (shares the cache with the thread theories panel). */
export function useInvestigations() {
  return useQuery<InvestigationV2[]>({
    queryKey: theoryKeys.investigations,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/investigations");
      if (error || !data) throw new Error("Failed to load investigations");
      return data;
    },
  });
}

export type LiveGraphState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "empty" }
  | { status: "ready"; model: GraphModel; partial: boolean };

/**
 * The person's whole graph, assembled from their threads' subgraphs plus the
 * memories, results, patterns, open loops and investigations that enrich it.
 * Threads and subgraphs are required; the enrichments degrade gracefully.
 */
export function useLiveGraph(): LiveGraphState {
  const threadsQuery = useThreads();
  const threads = useMemo(() => threadsQuery.data ?? [], [threadsQuery.data]);
  const ids = threads.map((t) => t.id);
  const graphQueries = useGraphsForThreads(ids);
  const memoryQueries = useMemoriesForThreads(ids);
  const pendingQuery = usePendingItems();
  const patternsQuery = usePatterns();
  const resultsQuery = useResults();
  const investigationsQuery = useInvestigations();

  const secondary = [pendingQuery, patternsQuery, resultsQuery, investigationsQuery];
  const loading =
    threadsQuery.isLoading ||
    graphQueries.some((q) => q.isLoading) ||
    memoryQueries.some((q) => q.isLoading) ||
    secondary.some((q) => q.isLoading);
  const allGraphsFailed = graphQueries.length > 0 && graphQueries.every((q) => q.isError);
  const partial =
    graphQueries.some((q) => q.isError) || memoryQueries.some((q) => q.isError) || secondary.some((q) => q.isError);

  const version = [
    threadsQuery.dataUpdatedAt,
    ...graphQueries.map((q) => q.dataUpdatedAt),
    ...memoryQueries.map((q) => q.dataUpdatedAt),
    ...secondary.map((q) => q.dataUpdatedAt),
  ].join(",");

  const model = useMemo(
    () =>
      buildLiveGraph({
        threads,
        graphs: graphQueries.map((q) => q.data),
        memories: memoryQueries.map((q) => q.data),
        pending: pendingQuery.data,
        patterns: patternsQuery.data?.patterns,
        results: resultsQuery.data?.analytes,
        investigations: investigationsQuery.data,
      }),
    // Query result arrays are new every render; `version` tracks real data changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [threads, version],
  );

  if (threadsQuery.isError || allGraphsFailed) return { status: "error" };
  if (loading) return { status: "loading" };
  if (threads.length === 0) return { status: "empty" };
  return { status: "ready", model, partial };
}
