"use client";

import { useQuery } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";
import { useSession } from "./useSession";

type Schemas = components["schemas"];

export type RangePosition = NonNullable<Schemas["ObservationV2"]["range_position"]>;
export type Observation = Omit<Schemas["ObservationV2"], "range_position"> & {
  range_position: RangePosition;
};
export type AnalyteResult = Omit<Schemas["AnalyteResultV2"], "latest" | "history" | "threads"> & {
  latest: Observation;
  history: Observation[];
  threads: Schemas["ThreadRefV2"][];
};
export type ResultsResponse = Omit<Schemas["ResultsResponseV2"], "analytes"> & {
  analytes: AnalyteResult[];
};
export type DocumentProcessingStatus = Schemas["DocumentProcessingStatus"];

export type DocumentRecord = Omit<
  Schemas["DocumentV2"],
  "extracted" | "extracted_total" | "result_count" | "original_filename" | "processing_status"
> & {
  extracted: Schemas["ExtractedCountV2"][];
  extracted_total: number;
  result_count: number;
  /** Sanitised name of the uploaded file; null for older uploads (use display_label). */
  original_filename: string | null;
  processing_status: DocumentProcessingStatus;
};
export type DocumentsResponse = Omit<Schemas["DocumentsResponseV2"], "documents"> & {
  documents: DocumentRecord[];
};

export const recordsKeys = {
  results: ["records", "results"] as const,
  documents: ["records", "documents"] as const,
};

/** How often to re-check while a document is still waiting to be read. */
const WAITING_REFETCH_MS = 20_000;

const LEGACY_PROCESSING_STATUS: Record<Schemas["DocumentStatus"], DocumentProcessingStatus> = {
  processed: "processed",
  waiting: "received",
  could_not_read: "needs_ocr",
};

/** Statuses where WellBe is still working on the document. */
export function isDocumentInProgress(status: DocumentProcessingStatus): boolean {
  return status === "received" || status === "processing";
}

function toObservation(o: Schemas["ObservationV2"]): Observation {
  return { ...o, range_position: o.range_position ?? "not_compared" };
}

function toResults(r: Schemas["ResultsResponseV2"]): ResultsResponse {
  return {
    ...r,
    analytes: (r.analytes ?? []).map((a) => ({
      ...a,
      latest: toObservation(a.latest),
      history: (a.history ?? []).map(toObservation),
      threads: a.threads ?? [],
    })),
  };
}

function toDocuments(r: Schemas["DocumentsResponseV2"]): DocumentsResponse {
  return {
    ...r,
    documents: (r.documents ?? []).map((d) => ({
      ...d,
      extracted: d.extracted ?? [],
      extracted_total: d.extracted_total ?? 0,
      result_count: d.result_count ?? 0,
      original_filename: d.original_filename?.trim() || null,
      processing_status: d.processing_status ?? LEGACY_PROCESSING_STATUS[d.status],
    })),
  };
}

function useSignedIn(): boolean | undefined {
  const session = useSession();
  if (session === undefined) return undefined;
  return Boolean(session?.patientId);
}

/** Lab / vital observations grouped by analyte, from /v2/results. */
export function useResults() {
  const signedIn = useSignedIn();
  const query = useQuery<ResultsResponse>({
    queryKey: recordsKeys.results,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/results");
      if (error || !data) throw new Error("Failed to load results");
      return toResults(data);
    },
    enabled: signedIn === true,
  });
  return { ...query, signedIn };
}

/** Uploaded documents with processing state, from /v2/documents. */
export function useDocuments() {
  const signedIn = useSignedIn();
  const query = useQuery<DocumentsResponse>({
    queryKey: recordsKeys.documents,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/documents");
      if (error || !data) throw new Error("Failed to load documents");
      return toDocuments(data);
    },
    enabled: signedIn === true,
    refetchInterval: (q) =>
      q.state.data?.documents.some((d) => isDocumentInProgress(d.processing_status))
        ? WAITING_REFETCH_MS
        : false,
  });
  return { ...query, signedIn };
}
