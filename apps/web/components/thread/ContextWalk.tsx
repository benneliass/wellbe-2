"use client";

import { useState } from "react";
import { Button } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import styles from "./ThreadDetailLive.module.css";

type ExploreBody = components["schemas"]["ContextExploreRequest"];
type ExplorePage = components["schemas"]["ContextExploreResponse"];

/**
 * Starts the person's raw-context walk from a record they already opened.
 * A filter stays on that record. A neighbour route steps once.
 */
export function ContextWalk({ captureId }: { captureId: string }) {
  const [page, setPage] = useState<ExplorePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function explore(body: ExploreBody) {
    setPending(true);
    setError(null);
    const { data, error: failed } = await getApiClient().POST("/v2/context/explore", { body });
    setPending(false);
    if (failed || !data) {
      setError("Couldn't open related context. Try again.");
      return;
    }
    setPage(data);
  }

  if (!page) {
    return (
      <div className={styles.walk}>
        <Button
          size="sm"
          variant="ghost"
          disabled={pending}
          onClick={() =>
            void explore({
              purpose: "look",
              request_id: crypto.randomUUID(),
              anchor_id: captureId,
              hold_at_anchor: true,
              operation: "open",
            })
          }
        >
          {pending ? "Looking…" : "See what relates"}
        </Button>
        {error ? (
          <p className={styles.muted} role="alert">
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className={styles.walk}>
      <p className={styles.tlDetail}>{page.breadcrumb.join(" · ") || "This record"}</p>
      {page.detail ? <p className={styles.muted}>{page.detail}</p> : null}
      <div className={styles.walkRoutes}>
        {page.next_routes.map((route) => (
          <Button
            key={route.route_id}
            size="sm"
            variant="secondary"
            disabled={pending || !page.route_handle}
            onClick={() =>
              void explore({
                purpose: "look",
                request_id: crypto.randomUUID(),
                route_handle: page.route_handle,
                route_id: route.route_id,
                operation: "continue",
                hold_at_anchor: false,
              })
            }
          >
            {route.label}
          </Button>
        ))}
      </div>
      {error ? (
        <p className={styles.muted} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
