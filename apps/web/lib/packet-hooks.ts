"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "./api";

export type ShareLinkSummary = components["schemas"]["ShareLinkSummaryV2"];

export const packetQueryKeys = {
  shareLinks: ["share-links"] as const,
};

/** Every share link the person has created, newest first (/v2/share-links). */
export function useShareLinks() {
  return useQuery<ShareLinkSummary[]>({
    queryKey: packetQueryKeys.shareLinks,
    queryFn: async () => {
      const { data, error } = await getApiClient().GET("/v2/share-links");
      if (error || !data) throw new Error("Failed to load your shares");
      return data;
    },
  });
}

/** Stops future access through one link. An exported copy can't be recalled. */
export function useRevokeShareLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ packetId, linkId }: { packetId: string; linkId: string }) => {
      const { error, response } = await getApiClient().POST(
        "/v2/visit-packets/{packet_id}/share/{link_id}/revoke",
        { params: { path: { packet_id: packetId, link_id: linkId } } },
      );
      if (error || !response.ok) throw new Error("Couldn't revoke this link. Please try again.");
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: packetQueryKeys.shareLinks }),
  });
}
