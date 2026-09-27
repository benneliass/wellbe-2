"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Chip, Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { StateNote } from "@/components/placeholder/StateNote";
import { formatShortDate } from "@/lib/adapters";
import { nodeTypeLabel, relationPhrase } from "@/lib/graph-labels";
import { useGraphsForThreads, useThreads } from "@/lib/hooks";
import type { ThreadSummary } from "@/lib/types";
import styles from "./PersonGraph.module.css";

type GraphNodeV2 = components["schemas"]["GraphNodeV2"];
type GraphEdgeV2 = components["schemas"]["GraphEdgeV2"];
type ThreadSubgraphV2 = components["schemas"]["ThreadSubgraphV2"];

const W = 860;
const H = 560;
const HUES = ["#0ea5a4", "#8b5cf6", "#f59e0b", "#0284c7", "#db2777", "#16a34a", "#64748b"];

interface Hub {
  thread: ThreadSummary;
  x: number;
  y: number;
  hue: string;
}

interface PlacedNode {
  node: GraphNodeV2;
  x: number;
  y: number;
  threadIds: string[];
}

interface Layout {
  hubs: Hub[];
  nodes: PlacedNode[];
  edges: GraphEdgeV2[];
}

function shortLabel(label: string, max = 26): string {
  return label.length > max ? `${label.slice(0, max - 1).trimEnd()}…` : label;
}

/**
 * Deterministic layout: each thread is a hub on an ellipse; its concepts ring
 * around it. A concept that belongs to several threads sits between their hubs
 * (a bridge), so shared context is visible at a glance.
 */
function layout(threads: ThreadSummary[], graphs: (ThreadSubgraphV2 | undefined)[]): Layout {
  const k = threads.length;
  const hubs: Hub[] = threads.map((thread, i) => {
    const a = (i / Math.max(k, 1)) * Math.PI * 2 - Math.PI / 2;
    return {
      thread,
      x: k === 1 ? W / 2 : W / 2 + Math.cos(a) * 280,
      y: k === 1 ? H / 2 : H / 2 + Math.sin(a) * 170,
      hue: HUES[i % HUES.length]!,
    };
  });

  const membership = new Map<string, { node: GraphNodeV2; threadIds: string[] }>();
  const edges = new Map<string, GraphEdgeV2>();
  graphs.forEach((g, i) => {
    const tid = threads[i]!.id;
    for (const n of g?.nodes ?? []) {
      const m = membership.get(n.id) ?? { node: n, threadIds: [] };
      if (!m.threadIds.includes(tid)) m.threadIds.push(tid);
      membership.set(n.id, m);
    }
    for (const e of g?.edges ?? []) edges.set(e.id, e);
  });

  const hubById = new Map(hubs.map((h) => [h.thread.id, h]));
  const perHub = new Map<string, number>();
  const nodes: PlacedNode[] = [];
  const bridgeGroups = new Map<string, number>();
  for (const { threadIds } of membership.values()) {
    if (threadIds.length > 1) {
      const key = [...threadIds].sort().join("|");
      bridgeGroups.set(key, (bridgeGroups.get(key) ?? 0) + 1);
    }
  }
  const bridgeSeen = new Map<string, number>();
  for (const { node, threadIds } of membership.values()) {
    const owners = threadIds.map((t) => hubById.get(t)).filter((h): h is Hub => Boolean(h));
    if (owners.length > 1) {
      // Spread bridges along the perpendicular of the line joining their hubs.
      const key = [...threadIds].sort().join("|");
      const total = bridgeGroups.get(key) ?? 1;
      const i = bridgeSeen.get(key) ?? 0;
      bridgeSeen.set(key, i + 1);
      const cx = owners.reduce((s, h) => s + h.x, 0) / owners.length;
      const cy = owners.reduce((s, h) => s + h.y, 0) / owners.length;
      const dx = owners[1]!.x - owners[0]!.x;
      const dy = owners[1]!.y - owners[0]!.y;
      const len = Math.hypot(dx, dy) || 1;
      const off = (i - (total - 1) / 2) * 110;
      nodes.push({ node, threadIds, x: cx + (-dy / len) * off, y: cy + (dx / len) * off });
      continue;
    }
    const hub = owners[0]!;
    const j = perHub.get(hub.thread.id) ?? 0;
    perHub.set(hub.thread.id, j + 1);
    // Push satellites away from the canvas centre so they don't collide with bridges.
    const out = Math.atan2(hub.y - H / 2, hub.x - W / 2);
    const a = (k === 1 ? 0 : out) + j * 0.9;
    nodes.push({ node, threadIds, x: hub.x + Math.cos(a) * 78, y: hub.y + Math.sin(a) * 62 });
  }
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  for (const p of nodes) {
    p.x = clamp(p.x, 70, W - 70);
    p.y = clamp(p.y, 30, H - 30);
  }
  return { hubs, nodes, edges: Array.from(edges.values()) };
}

export function PersonGraph() {
  const threadsQuery = useThreads();
  const threads = useMemo(() => threadsQuery.data ?? [], [threadsQuery.data]);
  const graphQueries = useGraphsForThreads(threads.map((t) => t.id));
  const [view, setView] = useState<"graph" | "list">("graph");
  const [selected, setSelected] = useState<string | null>(null);

  const loadingGraphs = graphQueries.some((q) => q.isLoading);
  const failedGraphs = graphQueries.filter((q) => q.isError).length;
  const graphData = graphQueries.map((q) => q.data);
  const graphKey = graphQueries.map((q) => q.dataUpdatedAt).join(",");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const model = useMemo(() => layout(threads, graphData), [threads, graphKey]);

  if (threadsQuery.isLoading || (threads.length > 0 && loadingGraphs)) {
    return <StateNote icon="git-fork" title="Mapping your records…" />;
  }
  if (threadsQuery.isError) {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your graph"
        description="Please try again in a moment."
      />
    );
  }
  if (threads.length === 0) {
    return (
      <StateNote
        icon="git-fork"
        title="Nothing to map yet"
        description="As you add symptoms, results, and notes, WellBe maps how they connect — traceable to the source, never a diagnosis."
      />
    );
  }

  const nodeById = new Map(model.nodes.map((p) => [p.node.id, p]));
  const hubById = new Map(model.hubs.map((h) => [h.thread.id, h]));
  const sel = selected ? nodeById.get(selected) : undefined;

  return (
    <div className={styles.wrap}>
      <div className={styles.bar}>
        <div className={styles.tabs} role="tablist" aria-label="Graph view">
          {(["graph", "list"] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              className={styles.tab}
              data-active={view === v || undefined}
              onClick={() => setView(v)}
            >
              {v === "graph" ? "Map" : "List"}
            </button>
          ))}
        </div>
        <span className={styles.summary}>
          {model.hubs.length} {model.hubs.length === 1 ? "concern" : "concerns"} ·{" "}
          {model.nodes.length} connected {model.nodes.length === 1 ? "item" : "items"}
        </span>
      </div>

      {failedGraphs > 0 && (
        <p className={styles.note}>
          <Icon name="info" size={13} /> Some connections couldn&rsquo;t be loaded right now.
        </p>
      )}

      <div className={styles.body}>
        {view === "graph" ? (
          <svg
            className={styles.canvas}
            viewBox={`0 0 ${W} ${H}`}
            role="img"
            aria-label="Map of your concerns and what they connect to"
          >
            {model.nodes.flatMap((p) =>
              p.threadIds.map((tid) => {
                const h = hubById.get(tid);
                if (!h) return null;
                return (
                  <line
                    key={`${tid}-${p.node.id}`}
                    x1={h.x}
                    y1={h.y}
                    x2={p.x}
                    y2={p.y}
                    stroke={h.hue}
                    strokeOpacity={0.35}
                    strokeDasharray="3 5"
                  />
                );
              }),
            )}
            {model.edges.map((e) => {
              const a = nodeById.get(e.source);
              const b = nodeById.get(e.target);
              if (!a || !b) return null;
              return (
                <line
                  key={e.id}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className={styles.edge}
                  strokeWidth={1 + e.evidence_weight * 3}
                >
                  <title>{`${a.node.label} ${relationPhrase(e.relation)} ${b.node.label}`}</title>
                </line>
              );
            })}
            {model.hubs.map((h) => (
              <g key={h.thread.id} className={styles.hub}>
                <circle cx={h.x} cy={h.y} r={34} fill={h.hue} fillOpacity={0.14} stroke={h.hue} />
                <text x={h.x} y={h.y + 4} textAnchor="middle" className={styles.hubLabel} fill={h.hue}>
                  {shortLabel(h.thread.title, 18)}
                </text>
              </g>
            ))}
            {model.nodes.map((p) => {
              const hue = p.threadIds.length > 1 ? "#475569" : hubById.get(p.threadIds[0]!)?.hue ?? "#475569";
              return (
                <g
                  key={p.node.id}
                  className={styles.node}
                  data-selected={selected === p.node.id || undefined}
                  role="button"
                  tabIndex={0}
                  aria-label={`${p.node.label}, ${nodeTypeLabel(p.node.type)}`}
                  onClick={() => setSelected(p.node.id)}
                  onKeyDown={(ev) => {
                    if (ev.key === "Enter" || ev.key === " ") setSelected(p.node.id);
                  }}
                >
                  <circle cx={p.x} cy={p.y} r={9} fill="#fff" stroke={hue} strokeWidth={2.5} />
                  <text x={p.x} y={p.y + 24} textAnchor="middle" className={styles.nodeLabel}>
                    {shortLabel(p.node.label)}
                  </text>
                </g>
              );
            })}
          </svg>
        ) : (
          <div className={styles.list}>
            {model.hubs.map((h) => {
              const items = model.nodes.filter((p) => p.threadIds.includes(h.thread.id));
              return (
                <section key={h.thread.id} className={styles.listGroup} aria-label={h.thread.title}>
                  <header className={styles.listHead}>
                    <span className={styles.dot} style={{ background: h.hue }} />
                    <Link href={`/threads/${h.thread.id}`} className={styles.listTitle}>
                      {h.thread.title}
                    </Link>
                    <span className={styles.summary}>{items.length} connected</span>
                  </header>
                  <ul>
                    {items.map((p) => (
                      <li key={p.node.id}>
                        <button type="button" className={styles.listRow} onClick={() => setSelected(p.node.id)}>
                          <span>{p.node.label}</span>
                          <Chip size="sm">{nodeTypeLabel(p.node.type)}</Chip>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}

        <aside className={styles.panel} aria-label="Details">
          {sel ? (
            <NodeDetail placed={sel} edges={model.edges} nodeById={nodeById} hubById={hubById} />
          ) : (
            <>
              <h2 className={styles.panelTitle}>How to read this</h2>
              <p className={styles.panelBody}>
                Each circle is a concern you&rsquo;re carrying; the dots around it are what your
                records link to it. A dot between two concerns is shared by both. Select one to see
                where it comes from.
              </p>
            </>
          )}
          <p className={styles.caveat}>
            <Icon name="lock" size={12} /> Scoped to you and traceable to its sources — links are not
            causes, and never a diagnosis.
          </p>
        </aside>
      </div>
    </div>
  );
}

function NodeDetail({
  placed,
  edges,
  nodeById,
  hubById,
}: {
  placed: PlacedNode;
  edges: GraphEdgeV2[];
  nodeById: Map<string, PlacedNode>;
  hubById: Map<string, Hub>;
}) {
  const n = placed.node;
  const seen = n.attributes?.first_seen_at;
  const first = typeof seen === "string" ? formatShortDate(seen) : "";
  const links = edges.filter((e) => e.source === n.id || e.target === n.id);
  return (
    <>
      <h2 className={styles.panelTitle}>{n.label}</h2>
      <div className={styles.panelMeta}>
        <Chip size="sm">{nodeTypeLabel(n.type)}</Chip>
        {first && <span>First noted {first}</span>}
      </div>
      <div className={styles.panelSection}>Part of</div>
      <ul className={styles.panelList}>
        {placed.threadIds.map((tid) => {
          const h = hubById.get(tid);
          return h ? (
            <li key={tid}>
              <Link href={`/threads/${tid}`}>{h.thread.title}</Link>
            </li>
          ) : null;
        })}
      </ul>
      {links.length > 0 && (
        <>
          <div className={styles.panelSection}>Connections</div>
          <ul className={styles.panelList}>
            {links.map((e) => (
              <li key={e.id}>
                <b>{nodeById.get(e.source)?.node.label ?? "An item"}</b> {relationPhrase(e.relation)}{" "}
                <b>{nodeById.get(e.target)?.node.label ?? "another item"}</b>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
