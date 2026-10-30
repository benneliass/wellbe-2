"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { EvidenceDrawer, type EvidenceSource, Icon, Tabs } from "@wellbe/ui";
import styles from "./GraphLive.module.css";
import {
  type Cluster,
  type ClusterId,
  FLOOR_LABEL,
  type GraphEdge,
  type GraphModel,
  type GraphNode,
  LAYERS,
  type LayerId,
  NEUTRAL_HUE,
} from "./graphData";
import { layersWithData } from "./liveGraphAdapter";
import { arrowDelta, clientToSvg, dragTo, loadPositions, passedThreshold, type Positions, savePositions, svgToGraph } from "./graphDrag";
import { canvasLabel, clusterHalo, clusterLabelBox, layoutGraph, nodeBox, nodeRadius, nodeLabelOffset, withSatelliteCounts, COMPACT_VIEW, type Pt, type ViewBox, WIDE_VIEW } from "./liveGraphLayout";
import { RecordCircle } from "./marks";
import { useMapEffects, MapConnection as SilkConnection, MapHoverTooltip as GraphHoverTooltip, useReducedMotion, useElementWidth, useTransientFlag, MapObjectFrame, MapFocusRing, MapAccents, MapGroupLight, useMapZoomBoundary, useMapRoutes, useMapPan } from "@wellbe/ui/map";
import { MAP_INTERACTION, MAP_MOTION, type MapCamera as Zoom } from "@wellbe/ui/map/core";
import { indexGraphSatellites, visibleGraphSatellites } from "./graphSatellites";
import { layoutExpandedGraph, revealMapFamily } from "./expandedGraphLayout";
import { graphColorConcerns, graphObjectColor } from "./graphAppearance";
import { RadialMenu, Banner, ConsentBanner, OverviewPanel, ExplainPanel, NodePanel, EdgePanel, ListView, Legend } from "./GraphPanels";
import { typeLabelOf, plural, graphConnectionId } from "./graphPresentation";
import { GraphObject } from "./GraphObject";
import { graphGroupLight } from './graphGroupLights';
import { graphGroupLabels } from './graphGroupLabels';
import { useGraphPins } from './useGraphPins';

export type GraphMode = "overview" | "detail" | "explore";
type Mode = GraphMode;
export type GraphNavigationProps = { viewMode?: GraphMode; onViewModeChange?: (mode: GraphMode) => void; modeNavigation?: ReactNode };
type ViewKind = "graph" | "list";
type Selection = { kind: "node"; id: string } | { kind: "edge"; edge: GraphEdge } | { kind: "none" };
type DrawerState = { title: string; claim: ReactNode; sources: EvidenceSource[] } | null;

const COMPACT_BELOW = 640;

const EMPTY_LAYER_NOTE: Partial<Record<LayerId, string>> = {
  correction: "You haven't linked anything yourself yet. Links you add are kept apart from source evidence.",
  investigation: "No investigations in your records yet.",
  external: "No external context is linked to your records yet.",
  continuity: "No open loops right now.",
  observation: "No source observations are attached yet.",
};

export function GraphLive({ model: input, notice, patientId, viewMode, onViewModeChange, modeNavigation }: { model: GraphModel; notice?: string; patientId?: string | null } & GraphNavigationProps) {
  const router = useRouter();
  const reducedMotion = useReducedMotion();
  const [colRef, colWidth] = useElementWidth<HTMLDivElement>();
  const view: ViewBox = input.autoLayout && colWidth !== null && colWidth < COMPACT_BELOW ? COMPACT_VIEW : WIDE_VIEW;
  const VIEW_W = view.width;
  const VIEW_H = view.height;

  const laid = useMemo(
    () => (input.autoLayout ? layoutGraph(input, view) : { model: withSatelliteCounts(input), extent: { width: view.width, height: view.height - view.gutter } }),
    [input, view],
  );
  const model = laid.model;
  const fit = useMemo<Zoom>(() => {
    const k = Math.min(1, VIEW_W / laid.extent.width, (VIEW_H - view.gutter) / laid.extent.height);
    return { k, tx: (VIEW_W - laid.extent.width * k) / 2, ty: 0 };
  }, [laid, VIEW_W, VIEW_H, view.gutter]);

  const lastStep = Math.max(0, model.timeline.labels.length - 1);
  const [mode, setMode] = useState<Mode>("detail");
  const [view2, setView] = useState<ViewKind>("graph");
  const [floor, setFloor] = useState(3);
  const [floorOpen, setFloorOpen] = useState(false);
  const [scrub, setScrub] = useState(lastStep);
  const [layers, setLayers] = useState<Record<LayerId, boolean>>(() => {
    const o = {} as Record<LayerId, boolean>;
    LAYERS.forEach((l) => (o[l.id] = l.defaultOn));
    return o;
  });
  const [selection, setSelection] = useState<Selection>({ kind: "none" });
  const [hovered, setHovered] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [zoom, setZoom] = useState<Zoom>(fit);
  const [home, setHome] = useState<Zoom>(fit);
  const [recentering, setRecentering] = useTransientFlag(360);
  const [homeSaved, setHomeSaved] = useTransientFlag(1400);
  const [radial, setRadial] = useState<{ id: string; xPct: number; yPct: number } | null>(null);
  const [showWeak, setShowWeak] = useState(false);
  const [evidenceAll, setEvidenceAll] = useState(false);
  const [lens, setLens] = useState(false);
  const [comparison, setComparison] = useState<"off" | "consent" | "on">("off");
  const [explain, setExplain] = useState(false);
  const [shareMode, setShareMode] = useState(false);
  const [shareSel, setShareSel] = useState<Set<string>>(new Set());
  const [linkFrom, setLinkFrom] = useState<string | null>(null);
  const [userEdges, setUserEdges] = useState<GraphEdge[]>([]);
  const [disputed, setDisputed] = useState<Set<string>>(new Set());
  const [drawer, setDrawer] = useState<DrawerState>(null);
  const holdTimer = useRef<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [moved, setMoved] = useState<Positions>({});
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const nodeDrag = useRef<{ pointerId: number; client: Pt; origin: Pt; start: Positions; active: boolean } | null>(null);
  const suppressClick = useRef(false);
  const viewKey = `${VIEW_W}x${VIEW_H}`;
  const pan = useMapPan({ camera: zoom, viewport: { width: VIEW_W, height: VIEW_H }, onChange: setZoom, onBackgroundClick: () => { if (!linkFrom && !shareMode) setSelection({ kind: 'none' }); } });
  useMapEffects(svgRef, reducedMotion, viewKey);
  useEffect(() => { if (viewMode && viewMode !== mode) onModeChange(viewMode); }, [viewMode]);
  useMapZoomBoundary(svgRef, zoomAt, () => setZoom(sceneFit), () => {
    pan.cancel();
    nodeDrag.current = null;
    clearHold();
    setDragging(false);
    suppressClick.current = true;
  });
  const storeFor = patientId ? `${patientId}|${viewKey}` : null;

  useLayoutEffect(() => {
    setZoom(fit);
    setHome(fit);
    setRadial(null);
  }, [fit]);
  useEffect(() => setScrub(lastStep), [lastStep]);

  const { pins, toggle: togglePin } = useGraphPins(patientId ?? (model.kind === "preview" ? "design-preview" : null));
  const baseNodes = useMemo(() => model.nodes.map((node) => Object.hasOwn(pins, node.id) ? { ...node, pinned: pins[node.id] } : node), [model.nodes, pins]);
  const baseEdges = model.edges;
  const baseClusters = model.clusters;

  // Positions the person dragged to, per patient and view; ids no longer on the map are ignored.
  useEffect(() => {
    if (!patientId || !storeFor) {
      setMoved({});
      setLoadedFor(null);
      return;
    }
    const ids = new Set([...model.nodes.map((n) => n.id), ...model.clusters.map((c) => `cluster:${c.id}`)]);
    setMoved(loadPositions(patientId, viewKey, ids));
    setLoadedFor(storeFor);
  }, [patientId, viewKey, storeFor, model]);
  useEffect(() => {
    if (patientId && storeFor && loadedFor === storeFor && !dragging) savePositions(patientId, viewKey, moved);
  }, [moved, dragging, patientId, viewKey, storeFor, loadedFor]);
  const hasData = useMemo(() => layersWithData(model), [model]);

  const clusterById = useMemo(() => {
    const m: Record<ClusterId, Cluster> = {};
    baseClusters.forEach((c) => (m[c.id] = c));
    return m;
  }, [baseClusters]);
  const hueOf = useCallback((id: ClusterId | undefined) => (id && clusterById[id]?.hue) || NEUTRAL_HUE.hue, [clusterById]);
  const clusterLabel = useCallback((id: ClusterId) => clusterById[id]?.label ?? "Concern", [clusterById]);
  const hrefOf = useCallback(
    (n: GraphNode) => {
      const id = n.cluster ?? n.bridge?.[0];
      return id ? clusterById[id]?.href : undefined;
    },
    [clusterById],
  );
  const actionsFor = useCallback(
    (n: GraphNode) => model.actions.filter((a) => (a.id === "open" ? Boolean(hrefOf(n)) : a.id === "link" ? model.canAuthorLinks : true)),
    [model.actions, model.canAuthorLinks, hrefOf],
  );

  const allEdges = useMemo(() => [...baseEdges, ...userEdges], [baseEdges, userEdges]);
  const nodeById = useMemo(() => {
    const m: Record<string, GraphNode> = {};
    baseNodes.forEach((n) => (m[n.id] = n));
    return m;
  }, [baseNodes]);

  const colorOfNode = useCallback((node: GraphNode) => graphObjectColor(node, nodeById, hueOf), [nodeById, hueOf]);

  const labelPos = useCallback(
    (c: Cluster): Pt => moved[`cluster:${c.id}`] ?? { x: c.labelX ?? c.cx, y: c.labelY ?? c.cy - c.ry + 24 },
    [moved],
  );
  const satellites = useMemo(() => indexGraphSatellites(baseNodes, colorOfNode), [baseNodes, colorOfNode]);
  const toggleRelated = useCallback((id: string) => {
    if (!satellites[id]?.related.length) return;
    setExpanded((previous) => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }, [satellites]);

  const effLayers = useMemo(() => ({ ...layers, investigation: layers.investigation || lens }), [layers, lens]);

  const nodeVisible = useCallback(
    (n: GraphNode) => {
      if (hidden.has(n.id)) return false;
      if (n.deferred && (!n.anchor || !expanded.has(n.anchor))) return false;
      if (n.aggregate && comparison !== "on") return false;
      if (!effLayers[n.layer]) return false;
      if (n.week > scrub) return false;
      if (mode === "overview") return n.primary || n.lensRole === "theory";
      return true;
    },
    [hidden, expanded, comparison, effLayers, scrub, mode],
  );
  const edgeVisible = useCallback(
    (e: GraphEdge) => {
      const a = nodeById[e.a];
      const b = nodeById[e.b];
      if (!a || !b) return false;
      if (!effLayers[e.layer]) return false;
      if (e.week > scrub) return false;
      if (!nodeVisible(a) || !nodeVisible(b)) return false;
      const exempt = e.f === "user" || e.f === "hypothesis" || e.f === "relevance";
      return exempt || e.s >= floor;
    },
    [nodeById, effLayers, scrub, nodeVisible, floor],
  );

  // Tab order walks concern by concern, top to bottom.
  const clusterOrder = useMemo(() => new Map(baseClusters.map((c, i) => [c.id, i])), [baseClusters]);
  const visibleNodes = useMemo(
    () =>
      baseNodes
        .filter(nodeVisible)
        .sort((p, q) => (clusterOrder.get(p.cluster ?? "") ?? 99) - (clusterOrder.get(q.cluster ?? "") ?? 99) || p.y - q.y),
    [baseNodes, nodeVisible, clusterOrder],
  );
  const visibleEdges = allEdges.filter(edgeVisible);
  const layoutRevision = useMemo(() => JSON.stringify([viewKey, visibleNodes.map((node) => node.id), baseNodes.map((node) => [node.id, node.x, node.y, node.satelliteCount])]), [viewKey, visibleNodes, baseNodes]);
  const previousScene = useRef<{ revision: string; positions: Positions } | null>(null);
  const dynamicScene = useMemo(() => {
    const scene = layoutExpandedGraph({
      nodes: visibleNodes, moved,
      // Headings yield to members after object placement.
      titles: [],
      extent: laid.extent,
      previous: previousScene.current?.revision === layoutRevision ? previousScene.current.positions : undefined,
      grabbed: dragging ? Object.keys(nodeDrag.current?.start ?? {}).filter((id) => !id.startsWith("cluster:")) : [],
      emphasis: Object.fromEntries(visibleNodes.map((node) => [node.id, selection.kind === 'node' && selection.id === node.id ? MAP_MOTION.selectedScale : hovered === node.id ? MAP_MOTION.hoverScale : 1])),
    });
    previousScene.current = { revision: layoutRevision, positions: scene.positions };
    return scene;
  }, [visibleNodes, moved, baseClusters, labelPos, laid.extent, dragging, layoutRevision, selection, hovered]);
  const positioned = dynamicScene.positions;
  const sceneFit = useMemo<Zoom>(() => {
    const k = Math.min(1, VIEW_W / dynamicScene.extent.width, (VIEW_H - view.gutter) / dynamicScene.extent.height);
    return { k, tx: (VIEW_W - dynamicScene.extent.width * k) / 2, ty: 0 };
  }, [VIEW_W, VIEW_H, view.gutter, dynamicScene.extent.width, dynamicScene.extent.height]);
  const np = useCallback((id: string) => positioned[id] ?? { x: nodeById[id]?.x ?? 0, y: nodeById[id]?.y ?? 0 }, [positioned, nodeById]);
  const groupLabels = useMemo(() => graphGroupLabels(baseClusters, visibleNodes, nodeById, np, labelPos, dynamicScene.extent, moved), [baseClusters, visibleNodes, nodeById, np, labelPos, dynamicScene.extent, moved]);
  const groupLabelPos = (cluster: Cluster) => groupLabels[`cluster:${cluster.id}`] ?? labelPos(cluster);
  const clusters = useMemo(() => baseClusters.map((cluster) => {
    const members = visibleNodes.filter((node) => !node.bridge && graphColorConcerns(node, nodeById).includes(cluster.id));
    if (!expanded.size && !Object.keys(moved).length) return cluster;
    const label = labelPos(cluster);
    const boxes = members.map((node) => nodeBox({ ...node, ...np(node.id) }));
    return { ...cluster, ...clusterHalo(clusterLabelBox(cluster, label.x, label.y), boxes), labelX: label.x, labelY: label.y };
  }), [baseClusters, visibleNodes, nodeById, moved, expanded.size, labelPos, np]);

  const previousExpanded = useRef<ReadonlySet<string>>(new Set());
  useLayoutEffect(() => {
    const opened = [...expanded].filter((id) => !previousExpanded.current.has(id));
    previousExpanded.current = expanded;
    if (!opened.length) return;
    const family = visibleNodes.filter((node) => opened.includes(node.id) || node.anchor && opened.includes(node.anchor));
    const boxes = family.map((node) => nodeBox({ ...node, ...np(node.id) }));
    setZoom((current) => revealMapFamily(boxes, current, { width: VIEW_W, height: VIEW_H - view.gutter }));
  }, [expanded, visibleNodes, np, VIEW_W, VIEW_H, view.gutter]);
  const openLoopCount = baseNodes.filter((n) => n.ghost && !hidden.has(n.id)).length;
  const conceptCount = baseNodes.filter((n) => n.layer === "concept" && !n.aggregate && !hidden.has(n.id)).length;
  // A canvas grown for a dense graph still opens on its concepts.
  const clusterBelow = Math.min(0.62, Math.max(0.45, fit.k * 0.9));
  const lod: "cluster" | "concept" | "detail" = zoom.k < clusterBelow ? "cluster" : zoom.k > 1.55 ? "detail" : "concept";
  const hoverNode = hovered ? nodeById[hovered] ?? null : null;

  const routingPoint = (id: string) => {
    const node = nodeById[id]!;
    return { ...np(id), r: nodeRadius(node), labelWidth: nodeBox(node).hw * 2, labelTop: nodeRadius(node) + nodeLabelOffset(node) - 15, labelBottom: nodeBox(node).down, allowUnderLabel: true };
  };
  const routingObstacles = (source: string, target: string) => [
    ...visibleNodes.filter((node) => node.id !== source && node.id !== target).map((node) => routingPoint(node.id)),
  ];
  const routedScene = useMapRoutes(visibleEdges.map((edge) => ({
    id: graphConnectionId(edge), a: routingPoint(edge.a), b: routingPoint(edge.b),
    obstacles: routingObstacles(edge.a, edge.b),
  })), dynamicScene.extent, dragging);

  const routesById = useMemo(() => new Map(routedScene.map((entry) => [entry.id, entry])), [routedScene]);

  const selectedNodeId = selection.kind === "node" ? selection.id : null;
  const neighbourIds = useMemo(() => {
    const set = new Set<string>();
    if (!selectedNodeId) return set;
    allEdges.forEach((e) => {
      if (e.a === selectedNodeId) set.add(e.b);
      if (e.b === selectedNodeId) set.add(e.a);
    });
    return set;
  }, [selectedNodeId, allEdges]);

  function onNodeActivate(id: string) {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    if (shareMode) {
      setShareSel((prev) => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
      return;
    }
    if (linkFrom) {
      if (linkFrom !== id) {
        setUserEdges((prev) => [...prev, { id: `local:${crypto.randomUUID()}`, a: linkFrom, b: id, s: 4, f: "user", layer: "correction", week: scrub }]);
        setLayers((p) => ({ ...p, correction: true }));
      }
      setLinkFrom(null);
      return;
    }
    setSelection({ kind: "node", id });
    setExplain(false);
    setShowWeak(false);
    setEvidenceAll(false);
    setRadial(null);
    toggleRelated(id);
  }
  function onModeChange(next: Mode) {
    setMode(next);
    onViewModeChange?.(next);
    setFloor(next === "overview" ? 5 : next === "explore" ? 1 : 3);
    setSelection({ kind: "none" });
    setRadial(null);
  }
  function focusCluster(c: Cluster) {
    onModeChange("detail");
    const k = Math.max(fit.k, 1.15);
    setRecentering(!reducedMotion);
    setZoom({ k, tx: VIEW_W / 2 - c.cx * k, ty: (VIEW_H - view.gutter) / 2 - c.cy * k });
  }
  function recenter() {
    setRecentering(!reducedMotion);
    const grown = dynamicScene.extent.width > laid.extent.width || dynamicScene.extent.height > laid.extent.height;
    setZoom(grown ? sceneFit : home);
    setRadial(null);
  }
  function saveHome() {
    setHome(zoom);
    setHomeSaved(true);
  }
  function runAction(action: string, id: string) {
    const node = nodeById[id];
    setRadial(null);
    if (!node) return;
    if (action === "ask") router.push(`/ask?q=${encodeURIComponent(`How does my ${node.label.toLowerCase()} connect to my other concerns?`)}`);
    else if (action === "packet") router.push("/prepare");
    else if (action === "open") { const href = hrefOf(node); if (href) router.push(href); }
    else if (action === "hide") { setHidden((p) => new Set(p).add(id)); setSelection({ kind: "none" }); }
    else if (action === "link" && model.canAuthorLinks) setLinkFrom(id);
  }
  function openRadial(id: string) {
    const n = nodeById[id];
    if (!n) return;
    const p = np(id);
    setSelection({ kind: "node", id });
    setRadial({ id, xPct: ((p.x * zoom.k + zoom.tx) / VIEW_W) * 100, yPct: ((p.y * zoom.k + zoom.ty) / VIEW_H) * 100 });
  }
  /** Arrow keys move focus to the nearest visible node in that direction. */
  function focusToward(id: string, key: string) {
    const dir = key === "ArrowLeft" ? [-1, 0] : key === "ArrowRight" ? [1, 0] : key === "ArrowUp" ? [0, -1] : [0, 1];
    const p = np(id);
    let best: { id: string; score: number } | null = null;
    for (const n of visibleNodes) {
      if (n.id === id) continue;
      const q = np(n.id);
      const dx = q.x - p.x, dy = q.y - p.y;
      const along = dx * dir[0]! + dy * dir[1]!;
      if (along <= 0) continue;
      const across = Math.abs(dx * dir[1]! - dy * dir[0]!);
      const score = along + across * 2;
      if (!best || score < best.score) best = { id: n.id, score };
    }
    if (!best) return;
    const el = svgRef.current?.querySelector<SVGGElement>(`[data-node-id="${CSS.escape(best.id)}"]`);
    el?.focus();
  }
  function zoomAt(factor: number, cx: number, cy: number) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || !Number.isFinite(factor) || factor <= 0) return;
    setZoom((z) => {
      const k = Math.min(MAP_INTERACTION.maxZoom, Math.max(MAP_INTERACTION.minZoom, z.k * factor));
      const r = k / z.k;
      const mx = ((cx - rect.left) / rect.width) * VIEW_W;
      const my = ((cy - rect.top) / rect.height) * VIEW_H;
      return { k, tx: mx - (mx - z.tx) * r, ty: my - (my - z.ty) * r };
    });
    setRadial(null);
  }
  /** Press on a node (or a concern title, which carries its concepts): drags once past the threshold. */
  function startDrag(ev: React.PointerEvent, start: Positions) {
    if (ev.pointerType === "mouse" && ev.button !== 0) return;
    suppressClick.current = false;
    const svg = svgRef.current;
    if (!svg) return;
    nodeDrag.current = { pointerId: ev.pointerId, client: { x: ev.clientX, y: ev.clientY }, origin: svgToGraph(clientToSvg(svg, ev.clientX, ev.clientY, { width: VIEW_W, height: VIEW_H }), zoom), start, active: false };
    try {
      (ev.currentTarget as Element).setPointerCapture?.(ev.pointerId);
    } catch {
      // Capture is best-effort (unsupported, or the pointer is already gone).
    }
  }
  function moveDrag(ev: React.PointerEvent) {
    const d = nodeDrag.current;
    if (!d || d.pointerId !== ev.pointerId) return;
    if (!d.active) {
      if (!passedThreshold(ev.clientX - d.client.x, ev.clientY - d.client.y)) return;
      d.active = true;
      clearHold();
      setDragging(true);
      setRadial(null);
    }
    ev.stopPropagation();
    const svg = svgRef.current;
    if (!svg) return;
    const at = svgToGraph(clientToSvg(svg, ev.clientX, ev.clientY, { width: VIEW_W, height: VIEW_H }), zoom);
    const next = dragTo(d.start, { x: at.x - d.origin.x, y: at.y - d.origin.y });
    setMoved((prev) => ({ ...prev, ...next }));
  }
  function endDrag(ev: React.PointerEvent) {
    const d = nodeDrag.current;
    if (!d || d.pointerId !== ev.pointerId) return;
    nodeDrag.current = null;
    try {
      (ev.currentTarget as Element).releasePointerCapture?.(ev.pointerId);
    } catch {
      // Already released.
    }
    if (!d.active) return;
    // A drag is not a click: keep the selection and skip the click that follows.
    ev.stopPropagation();
    suppressClick.current = ev.type === "pointerup";
    setDragging(false);
  }
  function startNodeDrag(ev: React.PointerEvent, id: string) {
    startDrag(ev, { [id]: np(id) });
  }
  function startClusterDrag(ev: React.PointerEvent, c: Cluster) {
    const start: Positions = { [`cluster:${c.id}`]: groupLabelPos(c) };
    baseNodes.forEach((n) => { if (n.cluster === c.id && !n.bridge) start[n.id] = np(n.id); });
    startDrag(ev, start);
  }
  function nudge(id: string, key: string, big: boolean) {
    const delta = arrowDelta(key, big);
    if (!delta) return;
    const p = np(id);
    setMoved((prev) => ({ ...prev, [id]: { x: p.x + delta.x, y: p.y + delta.y } }));
  }
  function resetLayout() {
    setMoved({});
  }
  useEffect(() => () => { if (holdTimer.current !== null) window.clearTimeout(holdTimer.current); }, []);
  function startHold(id: string) { clearHold(); holdTimer.current = window.setTimeout(() => openRadial(id), 480); }
  function clearHold() { if (holdTimer.current) window.clearTimeout(holdTimer.current); holdTimer.current = null; }
  const narration = useMemo(() => buildNarration(clusters, visibleNodes), [clusters, visibleNodes]);
  const emptyLayers = LAYERS.filter((l) => effLayers[l.id] && !hasData[l.id] && !l.defaultOn && EMPTY_LAYER_NOTE[l.id]);
  const hasInvestigation = hasData.investigation;
  const bridges = baseNodes.filter((n) => n.bridge && n.lensRole !== "theory" && !n.aggregate);
  const timelineSteps = model.timeline.labels;
  const openEvidence = useCallback((title: string, claim: ReactNode, sources: EvidenceSource[]) => setDrawer({ title, claim, sources }), []);

  return (
    <div className={styles.wrap}>
      {/* toolbar */}
      <div className={styles.toolbar}>
        {modeNavigation ?? <Tabs
          items={[
            { id: "overview", label: "Overview" },
            { id: "detail", label: "Cluster detail" },
            { id: "explore", label: "Explore all" },
          ]}
          value={mode}
          onChange={(id) => onModeChange(id as Mode)}
        />}
        <div className={styles.toolbarRight}>
          {hidden.size > 0 && <button type="button" className={styles.hiddenChip} onClick={() => setHidden(new Set())}><Icon name="eye" size={14} /> {hidden.size} hidden · restore</button>}
          <button type="button" className={styles.toolBtn} data-active={lens || undefined} aria-pressed={lens} title="Lens" onClick={() => { setLens((v) => !v); }}><Icon name="flask-conical" size={15} /> <span className={styles.toolLabel}>Lens</span></button>
          <button type="button" className={styles.toolBtn} data-active={comparison === "on" || undefined} aria-pressed={comparison === "on"} title="Compare" onClick={() => setComparison((c) => (c === "off" ? "consent" : "off"))}><Icon name="users" size={15} /> <span className={styles.toolLabel}>Compare</span></button>
          <button type="button" className={styles.toolBtn} data-active={shareMode || undefined} aria-pressed={shareMode} title="Share" onClick={() => { setShareMode((v) => !v); setShareSel(new Set()); }}><Icon name="share" size={15} /> <span className={styles.toolLabel}>Share</span></button>
          <button type="button" className={styles.toolBtn} data-active={explain || undefined} aria-pressed={explain} title="Explain" onClick={() => { setExplain((v) => !v); setSelection({ kind: "none" }); }}><Icon name="sparkles" size={15} /> <span className={styles.toolLabel}>Explain</span></button>
          <div className={styles.floorMenu}>
            <button type="button" className={styles.toolBtn} data-active={floorOpen || undefined} aria-expanded={floorOpen} title="Link strength" onClick={() => setFloorOpen((v) => !v)}><Icon name="sliders-horizontal" size={15} /> <span className={styles.toolLabel}>Link strength</span> <Icon name="chevron-down" size={13} /></button>
            {floorOpen && (
              <>
                <div className={styles.popBackdrop} onClick={() => setFloorOpen(false)} />
                <div className={styles.floorPop} role="dialog" aria-label="Link strength">
                  <span className={styles.floorPopHead}>Link strength</span>
                  <input type="range" className={styles.floor} min={1} max={6} step={1} value={floor} onChange={(e) => setFloor(Number(e.target.value))} aria-label="Link strength" aria-valuetext={FLOOR_LABEL[floor]} />
                  <span className={styles.floorOut}>{FLOOR_LABEL[floor]}</span>
                </div>
              </>
            )}
          </div>
          <div className={styles.viewToggle} role="tablist" aria-label="View">
            <button type="button" role="tab" aria-selected={view2 === "graph"} aria-label="Map" className={styles.viewBtn} data-active={view2 === "graph" || undefined} onClick={() => setView("graph")} title="Map view"><Icon name="git-fork" size={15} /></button>
            <button type="button" role="tab" aria-selected={view2 === "list"} aria-label="List" className={styles.viewBtn} data-active={view2 === "list" || undefined} onClick={() => setView("list")} title="List view (text equivalent)"><Icon name="list" size={15} /></button>
          </div>
        </div>
      </div>

      {/* filters: layer toggles (link strength lives in the toolbar popover) */}
      <div className={styles.filters}>
        <div className={styles.layerChips}>
          <span className={styles.filterLabel}>Layers</span>
          {LAYERS.map((l) => (
            <button key={l.id} type="button" className={styles.layerChip} data-on={effLayers[l.id] || undefined} data-empty={!hasData[l.id] || undefined} aria-pressed={effLayers[l.id]} title={hasData[l.id] ? undefined : "Nothing in your records for this layer yet"} disabled={l.id === "investigation" && lens} onClick={() => setLayers((p) => ({ ...p, [l.id]: !p[l.id] }))}>
              <Icon name={l.icon} size={13} /> {l.label}
            </button>
          ))}
        </div>
      </div>

      {notice && <p className={styles.noticeLine}><Icon name="info" size={13} /> {notice}</p>}

      <div className={styles.stage}>
        <div className={styles.canvasCol} ref={colRef}>
          {view2 === "graph" && mode === "overview" && (
            <div className={styles.clusterCards}>
              {clusters.map((c) => {
                const count = visibleNodes.filter((n) => graphColorConcerns(n, nodeById).includes(c.id)).length;
                const loops = visibleNodes.filter((n) => n.ghost && (n.cluster === c.id || n.bridge?.includes(c.id))).length;
                return (
                  <button key={c.id} type="button" className={styles.clusterCard} onClick={() => focusCluster(c)}>
                    <span className={styles.clusterDot} style={{ background: c.hue }} />
                    <span className={styles.clusterName}>{c.label}</span>
                    <span className={styles.clusterMeta}>{plural(count, "item")}{loops > 0 ? ` · ${plural(loops, "open loop")}` : ""}</span>
                    <span className={styles.clusterStatus} data-status={c.status}>{c.statusLabel ?? (c.status === "active" ? "Active" : c.status === "watch" ? "Worth reviewing" : "Resolved")}</span>
                  </button>
                );
              })}
            </div>
          )}

          <div className={styles.viewport}>
            <div className={styles.bannerStack}>
              {model.kind === "preview" && <Banner icon="info" tone="violet" text="Design preview with sample data — not your records." />}
              {linkFrom && <Banner icon="git-fork" tone="violet" text={`Pick another concept to link to “${nodeById[linkFrom]?.label}”.`} onCancel={() => setLinkFrom(null)} />}
              {shareMode && <Banner icon="share" tone="teal" text={`Select concepts to share — ${shareSel.size} selected.`} actionLabel={`Export ${shareSel.size} to visit packet`} onAction={() => router.push("/prepare")} onCancel={() => { setShareMode(false); setShareSel(new Set()); }} />}
              {comparison === "consent" && <ConsentBanner onAccept={() => setComparison("on")} onCancel={() => setComparison("off")} />}
              {comparison === "on" && !model.comparisonAvailable && <Banner icon="users" tone="violet" text="No aggregate comparison data is available yet, so nothing from other people is shown." onCancel={() => setComparison("off")} />}
              {lens && !hasInvestigation && <Banner icon="flask-conical" tone="violet" text="The lens highlights investigations — none are open in your records yet." onCancel={() => setLens(false)} />}
              {emptyLayers.filter((l) => !(l.id === "investigation" && lens)).map((l) => (
                <Banner key={l.id} icon={l.icon} tone="teal" text={EMPTY_LAYER_NOTE[l.id]!} onCancel={() => setLayers((p) => ({ ...p, [l.id]: false }))} />
              ))}
            </div>
          {view2 === "list" ? (
            <ListView clusters={clusters} visibleNodes={visibleNodes} onSelect={(id) => { setSelection({ kind: "node", id }); setExplain(false); }} selectedId={selectedNodeId} />
          ) : (
            <div className={styles.canvas} style={{ aspectRatio: `${VIEW_W} / ${VIEW_H}` }}>
              <p id="wb-graph-narration" className={styles.srOnly}>{narration}</p>
              <svg
                ref={svgRef}
                className={styles.svg}
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
                preserveAspectRatio="xMidYMid meet"
                role="group"
                aria-label="Map of your concerns and what they connect to"
                aria-describedby="wb-graph-narration"
                style={{ cursor: pan.gesture.current || dragging ? "grabbing" : shareMode ? "copy" : linkFrom ? "crosshair" : "grab" }}
                onPointerDown={pan.onPointerDown}
                onPointerMove={pan.onPointerMove}
                onPointerUp={pan.onPointerUp}
                onPointerLeave={pan.onPointerLeave}
                onPointerCancel={pan.onPointerCancel}
                onKeyDown={(e) => { if (e.key === "Escape") { setRadial(null); setSelection({ kind: "none" }); } }}
              >
                <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="#fcfdff" />

                <g data-graph-camera="" data-map-camera="" transform={`translate(${zoom.tx},${zoom.ty}) scale(${zoom.k})`} style={{ transition: recentering ? "transform 340ms var(--wb-ease)" : "none" }}>
                  {/* concern halos (thread layer) */}
                  {effLayers.thread && <g data-map-group-layer="" style={{ isolation: 'isolate' }} pointerEvents="none">
                    {clusters.map((c) => <MapGroupLight key={c.id} id={c.id} {...graphGroupLight(c, visibleNodes, nodeById, np, groupLabelPos(c), lod === 'cluster')} color={c.hue} opacity={c.status === 'resolved' ? 0.5 : 1} />)}
                  </g>}
                  {effLayers.thread && lod !== 'cluster' && clusters.map((c) => {
                    const count = visibleNodes.filter((n) => graphColorConcerns(n, nodeById).includes(c.id)).length;
                    const { x: lx, y: ly } = groupLabelPos(c);
                    return (
                      <g key={c.id} opacity={c.status === "resolved" ? 0.5 : 1} aria-hidden="true">
                          <g data-group-heading={c.id} data-drag data-cluster-drag={c.id} className={styles.dragHandle} onPointerDown={(ev) => startClusterDrag(ev, c)} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}>
                            <text x={lx} y={ly} textAnchor="middle" className={styles.clusterLabel} fill={c.dark}>{canvasLabel(c.label, 28)}</text>
                            <text x={lx} y={ly + 17} textAnchor="middle" className={styles.clusterCount} fill={c.dark}>{count} shown</text>
                          </g>
                      </g>
                    );
                  })}

                  {lod === "cluster" ? (
                    clusters.map((c) => {
                      const count = visibleNodes.filter((n) => graphColorConcerns(n, nodeById).includes(c.id)).length;
                      return (
                        <MapObjectFrame key={c.id} data-node objectId={`concern:${c.id}`} position={{ x: c.cx, y: c.cy }} radius={46} state={{ hot: hovered === `concern:${c.id}` }} accessibleLabel={`${c.label}, concern, ${plural(count, "item")}. Open cluster detail`} onMouseEnter={() => setHovered(`concern:${c.id}`)} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered(`concern:${c.id}`)} onBlur={() => setHovered(null)} onClick={() => focusCluster(c)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); focusCluster(c); } }}>
                          <g data-pebble-object="">
                            <MapFocusRing position={{ x: c.cx, y: c.cy }} radius={54} />
                            <RecordCircle x={c.cx} y={c.cy} r={46} color={c.hue} />
                            <MapAccents x={c.cx} y={c.cy} radius={46} color={c.hue} profile={{ name: "concern", kind: "none", period: 216000, dash: "20 80" }} />
                          <text x={c.cx} y={c.cy - 2} textAnchor="middle" className={styles.blobLabel}>{canvasLabel(c.label, 12)}</text>
                          <text x={c.cx} y={c.cy + 15} textAnchor="middle" className={styles.blobCount}>{count}</text>
                          </g>
                        </MapObjectFrame>
                      );
                    })
                  ) : (
                    <>
                      {/* edges */}
                      {visibleEdges.map((e) => {
                        const connectionId = graphConnectionId(e);
                        const planned = routesById.get(connectionId);
                        const strong = e.s >= 5;
                        const theoryEnd = nodeById[e.a]?.lensRole === "theory" || nodeById[e.b]?.lensRole === "theory";
                        const faded = (selectedNodeId && e.a !== selectedNodeId && e.b !== selectedNodeId) || (lens && e.layer !== "investigation" && !theoryEnd);
                        const isDisp = disputed.has(`${e.a}|${e.b}`);
                        const dash = e.f === "user" ? "1 7" : e.f === "conflict" || isDisp ? "8 6" : e.f === "hypothesis" ? "4 5" : e.f === "relevance" ? "2 6" : e.f === "cand" || e.s <= 3 ? "6 6" : undefined;
                        const members = (id: string) => nodeById[id] ? graphColorConcerns(nodeById[id], nodeById) : [];
                        const sourceCases = members(e.a), targetCases = members(e.b);
                        const sharedCase = sourceCases.find((id) => targetCases.includes(id));
                        // Relationship-specific colors retain their existing meaning; ordinary
                        // connections carry their concern's color and blend across concerns.
                        const semanticStroke = e.lens === "against" ? "#94a3b8" : e.lens === "for" ? "#0ea5a4" : e.f === "user" ? "#8b5cf6" : e.f === "conflict" ? "#f59e0b" : e.f === "hypothesis" ? "#8b5cf6" : undefined;
                        const stroke = semanticStroke ?? hueOf(sharedCase ?? sourceCases[0]);
                        const endStroke = semanticStroke ?? hueOf(sharedCase ?? targetCases[0]);
                        const touch = (id: string | null) => id && (e.a === id || e.b === id);
                        const selectedEdge = selection.kind === "edge" && selection.edge === e;
                        const active = !faded && Boolean(touch(hovered) || touch(selectedNodeId) || selectedEdge);
                        const flow = active && !reducedMotion;
                        return (
                          <SilkConnection
                            key={connectionId}
                            id={connectionId} source={e.a} target={e.b}
                            sourceSegment={sharedCase ?? sourceCases[0]} targetSegment={sharedCase ?? targetCases[0]} relationship={e.f}
                            preferredRoute={planned?.route ? { d: planned.route.d, a: planned.a, b: planned.b } : undefined}
                            peerRoutes={routedScene.flatMap((entry) => entry.id !== connectionId && entry.route ? [entry.route.points] : [])}
                            a={routingPoint(e.a)} b={routingPoint(e.b)}
                            obstacles={routingObstacles(e.a, e.b)}
                            viewport={dynamicScene.extent}
                            revision={`${VIEW_W}x${VIEW_H}|${visibleNodes.map((node) => node.id).join(",")}`}
                            calm={reducedMotion} interacting={dragging} hot={Boolean(touch(hovered))}
                            stroke={stroke} endStroke={endStroke} width={strong ? 1.7 : e.s >= 4 ? 1.35 : 1.1}
                            opacity={isDisp ? 0.3 : strong ? 0.72 : 0.5}
                            faded={Boolean(faded)} dash={dash} active={active} flow={Boolean(flow)}
                            onSelect={() => { setSelection({ kind: "edge", edge: e }); setExplain(false); }}
                          />
                        );
                      })}

                      {/* nodes */}
                      {visibleNodes.map((n) => {
                        const theory = n.lensRole === "theory";
                        const hue = colorOfNode(n);
                        return (
                          <GraphObject
                            key={n.id}
                            n={{ ...n, ...np(n.id) }}
                            hue={hue}
                            bridgeColors={n.bridge?.map(hueOf)}
                            bridgeBearings={n.bridge?.map((id, index) => {
                              const concern = clusters.find((cluster) => cluster.id === id);
                              const position = np(n.id);
                              return { index, angle: Math.atan2((concern?.cy ?? position.y) - position.y, (concern?.cx ?? position.x) - position.x) };
                            })}
                            orbitItems={visibleGraphSatellites(satellites[n.id], {
                              expanded: expanded.has(n.id), showSources: effLayers.observation,
                              conceptVisible: (id) => { const child = nodeById[id]; return Boolean(child && !hidden.has(id) && effLayers[child.layer] && child.week <= scrub); },
                            })}
                            childCount={satellites[n.id]?.related.length ?? 0}
                            dim={selectedNodeId && selectedNodeId !== n.id && !neighbourIds.has(n.id) ? 0.3 : lens && n.layer !== "investigation" && !neighbourIds.has(n.id) && !theory ? 0.55 : 1}
                            hot={hovered === n.id || selectedNodeId === n.id}
                            grabbed={Boolean(dragging && nodeDrag.current?.start[n.id])}
                            selected={selectedNodeId === n.id}
                            selectedForShare={shareSel.has(n.id)}
                            expandedNode={expanded.has(n.id)}
                            onTogglePin={() => togglePin(n.id, Boolean(n.pinned))}
                            onSelect={() => onNodeActivate(n.id)}
                            onContext={() => openRadial(n.id)}
                            onHoverIn={() => setHovered(n.id)}
                            onHoverOut={() => setHovered(null)}
                            onHoldStart={() => startHold(n.id)}
                            onHoldEnd={clearHold}
                            onArrow={(key) => focusToward(n.id, key)}
                            onNudge={(key, big) => nudge(n.id, key, big)}
                            onDragStart={(ev) => startNodeDrag(ev, n.id)}
                            onDragMove={moveDrag}
                            onDragEnd={endDrag}
                          />
                        );
                      })}
                    </>
                  )}
                </g>
              </svg>

              {radial && nodeById[radial.id] && <RadialMenu radial={radial} actions={actionsFor(nodeById[radial.id]!)} onAction={runAction} onClose={() => setRadial(null)} />}

              {hoverNode && !radial && !pan.gesture.current && !dragging && lod !== "cluster" && (
                <GraphHoverTooltip svg={svgRef} objectId={hoverNode.id} revision={`${zoom.k}|${zoom.tx}|${zoom.ty}|${visibleNodes.map((node) => node.id).join(',')}`}>
                  <span className={styles.ttTitle}>{hoverNode.label}</span>
                  <span className={styles.ttSub}>{typeLabelOf(hoverNode)}{hoverNode.ghost ? ` · ${hoverNode.statusNote ?? "awaiting result"}` : ` · ${plural(hoverNode.ev, "source")} · ${hoverNode.last}`}</span>
                </GraphHoverTooltip>
              )}

              <div className={styles.zoomControls} data-map-chrome="">
                <button type="button" className={styles.zoomBtn} aria-label="Zoom in" title="Zoom in" onClick={() => setZoom((z) => ({ ...z, k: Math.min(MAP_INTERACTION.maxZoom, z.k * 1.2) }))}><Icon name="plus" size={15} /></button>
                <button type="button" className={styles.zoomBtn} aria-label="Zoom out" title="Zoom out" onClick={() => setZoom((z) => ({ ...z, k: Math.max(MAP_INTERACTION.minZoom, z.k * 0.83) }))}><Icon name="chevron-down" size={15} /></button>
                <button type="button" className={styles.zoomBtn} aria-label="Recenter map" title="Recenter to default view" onClick={recenter}><Icon name="home" size={15} /></button>
                <button type="button" className={styles.zoomBtn} data-saved={homeSaved || undefined} aria-label="Set current view as default" title="Set current view as default" onClick={saveHome}><Icon name={homeSaved ? "check" : "star"} size={15} /></button>
                {Object.keys(moved).length > 0 && <button type="button" className={styles.zoomBtn} aria-label="Reset layout" title="Reset layout — put moved items back" onClick={resetLayout}><Icon name="rotate-ccw" size={15} /></button>}
              </div>
              <div className={styles.lodHint}>{lod === "cluster" ? "Concern overview" : lod === "detail" ? "Detail — evidence" : "Concepts"}{lens ? " · investigation lens" : ""}</div>
              <div className={styles.scrubDock} data-map-chrome="">
                <Icon name="clock" size={13} />
                {timelineSteps.length <= 1 ? (
                  <span className={styles.scrubSingle}>Replay · {model.timeline.valueTexts[0] ?? "Everything so far"}</span>
                ) : (
                  <div className={styles.scrubTrack}>
                    <div className={styles.scrubLine} />
                    <div className={styles.scrubFill} style={{ width: `calc((100% - 16px) * ${scrub / lastStep})` }} />
                    {timelineSteps.map((m, i) => (
                      <span key={`${m}-${i}`} className={styles.scrubTickMark} data-on={i <= scrub || undefined} style={{ left: `calc(8px + (100% - 16px) * ${i / lastStep})` }} />
                    ))}
                    <span className={styles.scrubHandle} style={{ left: `calc(8px + (100% - 16px) * ${scrub / lastStep})` }} />
                    <input type="range" className={styles.scrubA11y} min={0} max={lastStep} step={1} value={scrub} onChange={(e) => setScrub(Number(e.target.value))} aria-label="Replay timeline" aria-valuetext={model.timeline.valueTexts[scrub]} />
                    <div className={styles.scrubTicks} aria-hidden="true">
                      {timelineSteps.map((m, i) => (
                        <span key={`${m}-${i}`} className={styles.scrubTick} data-on={i <= scrub || undefined} style={{ left: `calc(8px + (100% - 16px) * ${i / lastStep})` }}>{m}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          </div>

          {view2 === "graph" && <Legend lens={lens} />}
        </div>

        <aside className={styles.inspector} aria-live="polite" aria-label="Details">
          {explain ? (
            <ExplainPanel narration={narration} onClose={() => setExplain(false)} />
          ) : selection.kind === "node" && nodeById[selection.id] ? (
            <NodePanel
              node={nodeById[selection.id]!}
              edges={allEdges}
              nodeById={nodeById}
              floor={floor}
              showWeak={showWeak}
              evidenceAll={evidenceAll}
              expandedNode={expanded.has(selection.id)}
              expandable={Boolean(satellites[selection.id]?.related.length)}
              actions={actionsFor(nodeById[selection.id]!)}
              hueOf={hueOf}
              onTogglePin={() => togglePin(selection.id, Boolean(nodeById[selection.id]?.pinned))}
              clusterLabel={clusterLabel}
              concernHref={hrefOf(nodeById[selection.id]!)}
              onAction={runAction}
              onSelectNeighbour={(id) => setSelection({ kind: "node", id })}
              onSelectEdge={(edge) => setSelection({ kind: "edge", edge })}
              onShowWeak={() => { setShowWeak(true); setFloor(1); }}
              onToggleEvidence={() => setEvidenceAll((v) => !v)}
              onToggleExpand={() => toggleRelated(selection.id)}
              onOpenEvidence={openEvidence}
            />
          ) : selection.kind === "edge" ? (
            <EdgePanel edge={selection.edge} nodeById={nodeById} canDispute={model.kind === "preview"} disputed={disputed.has(`${selection.edge.a}|${selection.edge.b}`)} onDispute={() => setDisputed((p) => new Set(p).add(`${selection.edge.a}|${selection.edge.b}`))} onOpenEvidence={openEvidence} onSelectNode={(id) => setSelection({ kind: "node", id })} />
          ) : (
            <OverviewPanel conceptCount={conceptCount} openLoopCount={openLoopCount} clusterCount={clusters.length} bridge={bridges[0]} bridgeConcerns={bridges[0]?.bridge?.map(clusterLabel) ?? []} bridgeCount={bridges.length} />
          )}
        </aside>
      </div>

      <EvidenceDrawer open={drawer !== null} onClose={() => setDrawer(null)} title={drawer?.title} claim={drawer?.claim} sources={drawer?.sources ?? []} />
    </div>
  );
}

export function buildNarration(clusters: Cluster[], nodes: GraphNode[]): string {
  const shown = clusters.filter((c) => nodes.some((n) => n.cluster === c.id || n.bridge?.includes(c.id)));
  if (!shown.length && !nodes.length) return "Your map is empty — add a capture to begin.";
  const loops = nodes.filter((n) => n.ghost);
  const bridges = nodes.filter((n) => n.bridge && n.lensRole !== "theory");
  const theories = nodes.filter((n) => n.lensRole === "theory");
  const parts: string[] = [];
  if (shown.length) parts.push(`You're carrying ${plural(shown.length, "concern")}: ${shown.map((c) => `${c.label} (${(c.statusLabel ?? (c.status === "watch" ? "worth reviewing" : c.status)).toLowerCase()})`).join(", ")}.`);
  if (bridges.length) parts.push(`${bridges.map((b) => b.label).join(" and ")} appear${bridges.length > 1 ? "" : "s"} across more than one concern, so ${bridges.length > 1 ? "they" : "it"} bridge${bridges.length > 1 ? "" : "s"} them in your records.`);
  if (theories.length) parts.push(`${plural(theories.length, "working idea")} from your investigations ${theories.length > 1 ? "are" : "is"} on the map — ideas, not conclusions.`);
  if (loops.length) parts.push(`${loops.length} open loop${loops.length > 1 ? "s are" : " is"} worth chasing: ${loops.map((l) => l.label).join(", ")}.`);
  parts.push("These are patterns recorded in your own sources — not a diagnosis or a claim of cause.");
  return parts.join(" ");
}
