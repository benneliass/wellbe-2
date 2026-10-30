"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import Link from "next/link";
import { Wordmark } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { CosmosField } from "./CosmosField";
import { RECORD_KINDS, RecordGlyph, type RecordKind } from "./marks";
import mapStyles from "./ContextMap.module.css";
import styles from "./GraphLive.module.css";
import { canvasLabel } from "./liveGraphLayout";

type MapNode = components["schemas"]["ContextMapNodeResponse"];
type MapBody = components["schemas"]["ContextMapResponse"];
type ExploreBody = components["schemas"]["ContextExploreRequest"];
type ExplorePage = components["schemas"]["ContextExploreResponse"];
type Route = components["schemas"]["ContextRouteResponse"];

function kindFor(node: MapNode): RecordKind {
  if (node.kind === "pseudonode") return "hub";
  if (node.source_type === "document" || node.source_type === "file") return "document";
  if (node.source_type === "result" || node.source_type === "lab") return "result";
  if (["note", "manual_text", "reported"].includes(node.source_type)) return "note";
  return "other";
}

// Deliberate sample constellation for comparing the implementation to option C.
// These positions are never used for a person's live records.
const REFERENCE_POSITIONS: Record<string, { x: number; y: number }> = {
  r01: { x: 0.25, y: 0.15 }, r02: { x: 0.52, y: 0.33 },
  r03: { x: 0.8, y: 0.15 }, r04: { x: 0.1, y: 0.48 },
  r05: { x: 0.27, y: 0.64 }, r06: { x: 0.79, y: 0.55 },
  r07: { x: 0.41, y: 0.89 }, r08: { x: 0.64, y: 0.87 },
  r09: { x: 0.89, y: 0.89 }, r10: { x: 0.15, y: 0.89 },
};
const SAMPLE_MAP: MapBody = {
  nodes: [
    { id: "r01", kind: "event", source_type: "note", degree: 1, label: "Monday note" },
    { id: "r02", kind: "event", source_type: "document", degree: 4, label: "Visit summary" },
    { id: "r03", kind: "event", source_type: "result", degree: 1, label: "Blood test PDF" },
    { id: "r04", kind: "event", source_type: "note", degree: 1, label: "Sleep note" },
    { id: "r05", kind: "pseudonode", source_type: "hub", degree: 4, label: "June capture" },
    { id: "r06", kind: "event", source_type: "document", degree: 3, label: "Prescription scan" },
    { id: "r07", kind: "event", source_type: "note", degree: 1, label: "Questions note" },
    { id: "r08", kind: "event", source_type: "result", degree: 1, label: "Lab attachment" },
    { id: "r09", kind: "event", source_type: "document", degree: 1, label: "Intake form" },
    { id: "r10", kind: "event", source_type: "audio", degree: 1, label: "Voice memo" },
  ],
  links: [
    { source: "r01", target: "r02", reason: "may relate" },
    { source: "r02", target: "r03", reason: "may relate" },
    { source: "r02", target: "r05", reason: "may relate" },
    { source: "r02", target: "r06", reason: "may relate" },
    { source: "r04", target: "r05", reason: "same capture" },
    { source: "r05", target: "r07", reason: "same capture" },
    { source: "r05", target: "r10", reason: "same capture" },
    { source: "r06", target: "r08", reason: "may relate" },
    { source: "r06", target: "r09", reason: "may relate" },
  ],
};

/**
 * The person's stored records and accepted links.
 * Porcelain marks share the knowledge graph's visual language. The walk matches the lab:
 * the full map opens first, a filter stays put, a neighbour steps once,
 * and clearing the choice returns to the full map.
 */
export function ContextMap({ preview = false, embedded = false }: { preview?: boolean; embedded?: boolean }) {
  const generation = useRef(0);
  const [selectedLink, setSelectedLink] = useState<{ source: string; target: string } | null>(null);
  const [data, setData] = useState<MapBody | null>(null);
  const [path, setPath] = useState<string[]>([]);
  const [handle, setHandle] = useState<string | null>(null);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [detail, setDetail] = useState("");
  const [stopped, setStopped] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (preview) {
      setData(SAMPLE_MAP);
      setLoading(false);
      return;
    }
    let live = true;
    void (async () => {
      const { data: body, error: failed } = await getApiClient().GET("/v2/context/map");
      if (!live) return;
      setLoading(false);
      if (failed || !body) {
        setError("Couldn't open your context map. Try again.");
        return;
      }
      setData(body);
    })();
    return () => {
      live = false;
    };
  }, []);

  const neighbours = useMemo(() => {
    const next = new Map<string, Set<string>>();
    for (const link of data?.links ?? []) {
      const left = next.get(link.source) ?? new Set<string>();
      left.add(link.target);
      next.set(link.source, left);
      const right = next.get(link.target) ?? new Set<string>();
      right.add(link.source);
      next.set(link.target, right);
    }
    return next;
  }, [data]);

  const tip = path[path.length - 1];
  const strong = new Set<string>(path);
  for (const other of neighbours.get(tip ?? "") ?? []) strong.add(other);

  function apply(page: ExplorePage) {
    setHandle(page.route_handle);
    setRoutes(page.terminal_reason === "supported_leaf" ? [] : page.next_routes);
    setDetail(page.detail);
    // An exhausted leaf still has a rewindable handle. Only ending the walk
    // explicitly (or losing its handle) prevents another choice.
    setStopped(Boolean(page.terminal_reason && page.terminal_reason !== "supported_leaf"));
  }

  async function explore(body: ExploreBody): Promise<ExplorePage | null> {
    const ticket = generation.current;
    setPending(true);
    setError(null);
    const { data: page, error: failed } = await getApiClient().POST("/v2/context/explore", { body });
    if (ticket !== generation.current) return null;
    setPending(false);
    if (failed || !page) {
      setError("Couldn't open related context. Try again.");
      return null;
    }
    apply(page);
    return page;
  }

  function localRoutes(id: string): Route[] {
    const next = [...(neighbours.get(id) ?? [])].map((other) => ({
      route_id: `open-${other}`,
      label: `Open ${other}`,
      kind: "neighbour",
    }));
    return [...next, { route_id: "facet-notes", label: "Only notes", kind: "facet" }, { route_id: "stop", label: "Stop here", kind: "fallback" }];
  }

  async function choose(id: string) {
    if (pending || stopped) return;
    setNotice(null); setSelectedLink(null);
    if (preview && path.length === 0) {
      setPath([id]);
      setHandle("preview");
      setRoutes(localRoutes(id));
      setStopped(false);
      return;
    }
    if (preview) {
      const earlier = path.indexOf(id);
      if (earlier >= 0 && earlier < path.length - 1) {
        setPath(path.slice(0, earlier + 1));
        setRoutes(localRoutes(id));
        return;
      }
      const opened = routes.find((item) => item.kind === "neighbour" && item.label === `Open ${id}`);
      if (opened) {
        setPath((current) => [...current, id]);
        setRoutes(localRoutes(id));
        return;
      }
      return;
    }
    if (path.length === 0) {
      const page = await explore({
        purpose: "look",
        request_id: crypto.randomUUID(),
        anchor_id: id,
        hold_at_anchor: true,
        operation: "open",
      });
      if (page?.route_handle) setPath([id]);
      return;
    }
    const earlier = path.indexOf(id);
    if (earlier >= 0 && earlier < path.length - 1 && handle) {
      const page = await explore({
        purpose: "look",
        request_id: crypto.randomUUID(),
        route_handle: handle,
        operation: "rewind",
        rewind_to_id: id,
        hold_at_anchor: false,
      });
      if (page) setPath(path.slice(0, earlier + 1));
      return;
    }
    const route = routes.find((item) => item.kind === "neighbour" && item.label === `Open ${id}`);
    if (route && handle) {
      const page = await explore({
        purpose: "look",
        request_id: crypto.randomUUID(),
        route_handle: handle,
        route_id: route.route_id,
        operation: "continue",
        hold_at_anchor: false,
      });
      if (page && page.terminal_reason !== "policy_blocked") setPath((current) => [...current, id]);
      return;
    }
  }

  async function follow(route: Route) {
    if (pending || stopped) return;
    if (preview && handle) {
      if (route.kind === "fallback") {
        setRoutes([]);
        setStopped(true);
        setDetail("You stopped here.");
        return;
      }
      if (route.kind === "neighbour") {
        const id = route.label.startsWith("Open ") ? route.label.slice(5) : "";
        if (id) setPath((current) => [...current, id]);
        setRoutes(id ? localRoutes(id) : []);
      }
      return;
    }
    if (!handle || pending) return;
    const page = await explore({
      purpose: "look",
      request_id: crypto.randomUUID(),
      route_handle: handle,
      route_id: route.route_id,
      operation: "continue",
      hold_at_anchor: false,
    });
    if (!page) return;
    if (route.kind === "fallback") { setStopped(true); return; }
    if (route.kind !== "neighbour") return;
    const id = route.label.startsWith("Open ") ? route.label.slice(5) : "";
    if (id && page.terminal_reason !== "policy_blocked") setPath((current) => [...current, id]);
  }

  function clearChoice() {
    generation.current += 1; setPending(false); setSelectedLink(null);
    setPath([]);
    setHandle(null);
    setRoutes([]);
    setDetail("");
    setStopped(false);
    setNotice(null);
  }

  if (loading) return <p className={styles.nodeMeta}>Loading your records…</p>;
  if (error && !data) {
    return (
      <p role="alert" className={styles.nodeMeta}>
        {error}
      </p>
    );
  }
  if (!data || data.nodes.length === 0) {
    return <p className={styles.nodeMeta}>Nothing stored yet. A record appears here after it is kept.</p>;
  }

  const routeLabels = path.map((id) => data.nodes.find((node) => node.id === id)?.label ?? id);

  return (
    <section className={mapStyles.map} data-preview={preview} data-embedded={embedded} aria-label="Context map">
      {!embedded && <header className={mapStyles.header}>
        <div className={mapStyles.titleRow}>
          <Wordmark size={24} />
          <nav className={mapStyles.tabs} aria-label="Record views">
            <Link href={preview ? "/design/graph" : "/graph"}>Graph</Link>
            <h1 aria-current="page">Context map</h1>
          </nav>
        </div>
        <p>Your records and the links you have kept.</p>
        {preview && <span className={mapStyles.preview}>Design preview · Sample records, not your data</span>}
      </header>}
      <div className={mapStyles.workspace} data-preview={preview}>
        <div className={mapStyles.canvas} style={{ "--record-count": data.nodes.length } as CSSProperties}>
          <CosmosField
            nodes={data.nodes.map((node) => ({
              id: node.id,
              label: canvasLabel(node.label),
              kind: kindFor(node),
              degree: node.degree,
              dim: path.length > 0 && !strong.has(node.id),
              pressed: node.id === tip,
              referencePosition: preview ? REFERENCE_POSITIONS[node.id] : undefined,
            }))}
            links={(data.links ?? []).map((link) => ({ source: link.source, target: link.target }))}
            path={path}
            selectedLink={selectedLink}
            onSelectLink={setSelectedLink}
            onClear={clearChoice}
            onSelect={(id) => void choose(id)}
          />
        </div>
        <aside className={styles.inspector} aria-label="Record details">
          <div className={styles.inspHead}><div><p className={styles.inspTitle}>{selectedLink ? 'Record connection' : tip ? data.nodes.find((node) => node.id === tip)?.label : 'Your stored records'}</p><p className={styles.inspSub}>{selectedLink ? [selectedLink.source, selectedLink.target].map((id) => data.nodes.find((node) => node.id === id)?.label ?? id).join(' / ') : tip ? 'Current record' : `${data.nodes.length} records · ${data.links.length} kept links`}</p></div></div>
          <p className={styles.inspBody}>{selectedLink ? (data.links.find((link) => (link.source === selectedLink.source && link.target === selectedLink.target) || (link.source === selectedLink.target && link.target === selectedLink.source))?.reason ?? 'These records may relate.') : tip ? 'The current record is gently enlarged. Choose one of its neighbours to take the next step, or an earlier record to step back.' : 'Choose a record to explore its accepted connections. A line means these records may relate.'}</p>
          <p className={styles.inspBody}>Drag an object to move it for this viewing. Record names move with their objects. The route buttons below keep each step in your hands.</p>
          <div className={styles.inspFoot}>These are your stored records and their links. Connections do not imply cause, importance, or a diagnosis.</div>
        </aside>
      </div>
      <footer className={mapStyles.footer}>
        <div className={mapStyles.route} aria-live="polite">
          {path.length > 0 ? <><span className={mapStyles.eyebrow}>Route history</span><span>{routeLabels.join(" / ")}</span></> : <span>Choose a record to begin.</span>}
        </div>
        <div className={mapStyles.bottomRow}>
          <div className={mapStyles.actions} aria-label="Next steps" aria-busy={pending}>
            {!stopped && routes.map((route) => (
              <button key={route.route_id} type="button" disabled={pending} onClick={() => void follow(route)}>{route.label}</button>
            ))}
            {path.length > 0 && <button type="button" disabled={pending} onClick={clearChoice}>Clear choice</button>}
          </div>
          <p className={mapStyles.helper}>A line means these records may relate.</p>
        </div>
        <div className={mapStyles.legend} aria-label="Record kinds">
          {(Object.entries(RECORD_KINDS) as [RecordKind, typeof RECORD_KINDS[RecordKind]][]).map(([kind, paint]) => (
            <span key={kind}><svg viewBox="0 0 24 24" width="16" height="16" style={{ color: paint.color }} aria-hidden="true"><RecordGlyph kind={kind} /></svg>{paint.label}</span>
          ))}
          <span className={mapStyles.sizeKey}>Size reflects links</span>
        </div>
        <div className={mapStyles.messages} role="status">{detail || notice}</div>
        {error && <p role="alert" className={mapStyles.error}>{error}</p>}
      </footer>
    </section>
  );
}
