"use client";

import { ConfidenceMeter, Icon, SourceMarker, type EvidenceSource } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import { nodeTypeLabel, relationPhrase } from "@/lib/graph-labels";
import { nodeSource, type SourceIndex } from "./thread-view";
import rec from "@/components/records/RecordList.module.css";
import styles from "./ThreadDetailLive.module.css";

export interface ConnectionNode {
  id: string;
  type: string;
  label: string;
  attributes?: Record<string, unknown>;
}

export interface ConnectionEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  evidence_weight?: number | null;
}

/** What this thread connects to in the person's own records — not causes. */
export function ThreadConnections({
  nodes,
  edges,
  index,
  labelOf,
  onOpenEvidence,
}: {
  nodes: readonly ConnectionNode[];
  edges: readonly ConnectionEdge[];
  index: SourceIndex;
  labelOf: (node: ConnectionNode) => string;
  onOpenEvidence: (title: string, claim: string, sources: EvidenceSource[]) => void;
}) {
  if (nodes.length === 0) return <p className={styles.muted}>No connected items yet.</p>;
  const byId = new Map(nodes.map((n) => [n.id, n]));

  return (
    <>
      <ul className={rec.list}>
        {nodes.map((n) => {
          const seen = n.attributes?.["first_seen_at"];
          const first = typeof seen === "string" ? formatShortDate(seen) : "";
          const elsewhere = n.attributes?.["in_thread"] === false;
          const src = nodeSource(n, index);
          const label = labelOf(n);
          return (
            <li key={n.id} className={rec.row}>
              <span className={rec.rowIcon}>
                <Icon name="activity" size={15} />
              </span>
              <span className={rec.rowMain}>
                <span className={rec.rowTitle}>{label}</span>
                <span className={rec.rowSub}>
                  {nodeTypeLabel(n.type)}
                  {first ? ` · first noted ${first}` : ""}
                  {elsewhere ? " · elsewhere in your records" : ""}
                </span>
              </span>
              <SourceMarker
                displayLabel={src.displayLabel}
                component={src.component}
                date={src.date}
                onOpen={() => onOpenEvidence("Where this came from", label, [src])}
              />
            </li>
          );
        })}
      </ul>
      {edges.length > 0 && (
        <ul className={styles.edges} aria-label="How these appear together">
          {edges.map((e) => {
            const from = byId.get(e.source);
            const to = byId.get(e.target);
            const phrase = `${from ? labelOf(from) : "An item"} ${relationPhrase(e.relation)} ${
              to ? labelOf(to) : "another item"
            }`;
            const sources = [from, to]
              .filter((n): n is ConnectionNode => Boolean(n))
              .map((n) => nodeSource(n, index));
            return (
              <li key={e.id} className={styles.edge}>
                <span>
                  <b>{from ? labelOf(from) : "An item"}</b> {relationPhrase(e.relation)}{" "}
                  <b>{to ? labelOf(to) : "another item"}</b>
                </span>
                <span className={styles.edgeMeta}>
                  <ConfidenceMeter score={e.evidence_weight ?? null} basisDisplay="none" />
                  {sources.length > 0 && (
                    <SourceMarker
                      displayLabel={sources[0]!.displayLabel}
                      component={sources[0]!.component}
                      count={sources.length}
                      onOpen={() => onOpenEvidence("Why these are connected", phrase, sources)}
                    />
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      <p className={styles.caveat}>Connections in your own records — not causes, and not a diagnosis.</p>
    </>
  );
}
