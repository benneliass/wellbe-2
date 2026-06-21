"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Chip, ConfidenceDots, Icon, SourceChip, Tabs } from "@wellbe/ui";
import styles from "./GraphLive.module.css";
import {
  CLUSTER_DARK,
  CLUSTER_HUE,
  type ClusterId,
  clusterLabel,
  FAMILY,
  type Family,
  FLOOR_LABEL,
  type GraphEdge,
  type GraphNode,
  LAYERS,
  type LayerId,
  NODE_ACTIONS,
  SEED_CLUSTERS,
  SEED_EDGES,
  SEED_NODES,
  sourceLabel,
  TYPE_ICON,
  TYPE_LABEL,
  WEEK_LABELS,
} from "./graphData";

type Mode = "overview" | "detail" | "explore";
type ViewKind = "graph" | "list";
type Selection = { kind: "node"; id: string } | { kind: "edge"; edge: GraphEdge } | { kind: "none" };

const VIEW_W = 860;
const VIEW_H = 686; // extra bottom gutter reserves room for the in-canvas timeline

export function GraphLive() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("detail");
  const [view, setView] = useState<ViewKind>("graph");
  const [floor, setFloor] = useState(3);
  const [floorOpen, setFloorOpen] = useState(false);
  const [scrub, setScrub] = useState(5);
  const [layers, setLayers] = useState<Record<LayerId, boolean>>(() => {
    const o = {} as Record<LayerId, boolean>;
    LAYERS.forEach((l) => (o[l.id] = l.defaultOn));
    return o;
  });
  const [selection, setSelection] = useState<Selection>({ kind: "none" });
  const [hovered, setHovered] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [zoom, setZoom] = useState({ k: 1, tx: 0, ty: 0 });
  const [home, setHome] = useState({ k: 1, tx: 0, ty: 0 });
  const [recentering, setRecentering] = useState(false);
  const [homeSaved, setHomeSaved] = useState(false);
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
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);
  const holdTimer = useRef<number | null>(null);

  const baseNodes = SEED_NODES;
  const baseEdges = SEED_EDGES;

  const allEdges = useMemo(() => [...baseEdges, ...userEdges], [baseEdges, userEdges]);
  const nodeById = useMemo(() => {
    const m: Record<string, GraphNode> = {};
    baseNodes.forEach((n) => (m[n.id] = n));
    return m;
  }, [baseNodes]);

  // dock deferred child concepts radially around their anchor (III.5 on-canvas expansion)
  const positioned = useMemo(() => {
    const m: Record<string, { x: number; y: number }> = {};
    baseNodes.forEach((n) => { if (!n.deferred) m[n.id] = { x: n.x, y: n.y }; });
    const kids: Record<string, GraphNode[]> = {};
    baseNodes.forEach((n) => { if (n.deferred && n.anchor) (kids[n.anchor] ??= []).push(n); });
    Object.entries(kids).forEach(([aid, list]) => {
      const a = m[aid] ?? { x: 430, y: 300 };
      list.forEach((k, i) => {
        const ang = -Math.PI / 2 + ((i + 0.5) / list.length) * Math.PI * 2;
        m[k.id] = { x: a.x + Math.cos(ang) * 94, y: a.y + Math.sin(ang) * 94 };
      });
    });
    return m;
  }, [baseNodes]);
  const np = useCallback((id: string) => positioned[id] ?? { x: nodeById[id]?.x ?? 0, y: nodeById[id]?.y ?? 0 }, [positioned, nodeById]);
  const deferredByAnchor = useMemo(() => {
    const m: Record<string, number> = {};
    baseNodes.forEach((n) => { if (n.deferred && n.anchor) m[n.anchor] = (m[n.anchor] ?? 0) + 1; });
    return m;
  }, [baseNodes]);

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

  const visibleNodes = baseNodes.filter(nodeVisible);
  const visibleEdges = allEdges.filter(edgeVisible);
  const openLoopCount = baseNodes.filter((n) => n.ghost && !hidden.has(n.id)).length;
  const conceptCount = baseNodes.filter((n) => n.layer === "concept" && !n.aggregate && !hidden.has(n.id)).length;
  const lod: "cluster" | "concept" | "detail" = zoom.k < 0.62 ? "cluster" : zoom.k > 1.55 ? "detail" : "concept";
  const hoverNode = hovered ? nodeById[hovered] ?? null : null;

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

  // capture children for on-canvas expansion (III.5 + observation layer XV.8)
  const captureChildren = useMemo(() => {
    if (!effLayers.observation) return [] as Array<{ id: string; px: number; py: number; x: number; y: number; source: string; parent: string }>;
    const out: Array<{ id: string; px: number; py: number; x: number; y: number; source: string; parent: string }> = [];
    expanded.forEach((pid) => {
      const p = nodeById[pid];
      if (!p || !p.captures || !nodeVisible(p)) return;
      const caps = p.captures.slice(0, 6);
      caps.forEach((c, i) => {
        const ang = -Math.PI / 2 + (i / Math.max(caps.length, 1)) * Math.PI * 2;
        out.push({ id: `cap-${pid}-${i}`, px: p.x, py: p.y, x: p.x + Math.cos(ang) * 64, y: p.y + Math.sin(ang) * 64, source: c.source, parent: pid });
      });
    });
    return out;
  }, [expanded, effLayers.observation, nodeById, nodeVisible]);

  function onNodeActivate(id: string) {
    if (shareMode) {
      setShareSel((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
      return;
    }
    if (linkFrom) {
      if (linkFrom !== id) {
        setUserEdges((prev) => [...prev, { a: linkFrom, b: id, s: 4, f: "user", layer: "correction", week: scrub }]);
        setLayers((p) => ({ ...p, correction: true }));
      }
      setLinkFrom(null);
      return;
    }
    setSelection({ kind: "node", id });
    setShowWeak(false);
    setEvidenceAll(false);
    setRadial(null);
    setExpanded((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }); // tap-again expands/collapses
  }
  function onModeChange(next: Mode) {
    setMode(next);
    setFloor(next === "overview" ? 5 : next === "explore" ? 1 : 3);
    setSelection({ kind: "none" });
    setRadial(null);
  }
  function recenter() {
    setRecentering(true);
    setZoom(home);
    setRadial(null);
    window.setTimeout(() => setRecentering(false), 360);
  }
  function saveHome() {
    setHome(zoom);
    setHomeSaved(true);
    window.setTimeout(() => setHomeSaved(false), 1400);
  }
  function runAction(action: string, id: string) {
    const node = nodeById[id];
    setRadial(null);
    if (!node) return;
    if (action === "ask") router.push(`/ask?q=${encodeURIComponent(`How does my ${node.label.toLowerCase()} connect to my other concerns?`)}`);
    else if (action === "packet") router.push("/prepare");
    else if (action === "hide") { setHidden((p) => new Set(p).add(id)); setSelection({ kind: "none" }); }
    else if (action === "link") setLinkFrom(id);
  }
  function openRadial(id: string) {
    const n = nodeById[id];
    if (!n) return;
    const p = np(id);
    setSelection({ kind: "node", id });
    setRadial({ id, xPct: ((p.x * zoom.k + zoom.tx) / VIEW_W) * 100, yPct: ((p.y * zoom.k + zoom.ty) / VIEW_H) * 100 });
  }
  function onWheel(ev: React.WheelEvent) {
    ev.preventDefault();
    const factor = ev.deltaY < 0 ? 1.12 : 0.89;
    const rect = ev.currentTarget.getBoundingClientRect();
    const cx = ev.clientX, cy = ev.clientY;
    setZoom((z) => {
      const k = Math.min(2.6, Math.max(0.4, z.k * factor));
      const r = k / z.k;
      const mx = ((cx - rect.left) / rect.width) * VIEW_W;
      const my = ((cy - rect.top) / rect.height) * VIEW_H;
      return { k, tx: mx - (mx - z.tx) * r, ty: my - (my - z.ty) * r };
    });
    setRadial(null);
  }
  function onPointerDown(ev: React.PointerEvent) {
    if ((ev.target as Element).closest("[data-node]")) return;
    drag.current = { x: ev.clientX, y: ev.clientY, tx: zoom.tx, ty: zoom.ty, moved: false };
  }
  function onPointerMove(ev: React.PointerEvent) {
    if (!drag.current) return;
    const rect = ev.currentTarget.getBoundingClientRect();
    const dx = ((ev.clientX - drag.current.x) / rect.width) * VIEW_W;
    const dy = ((ev.clientY - drag.current.y) / rect.height) * VIEW_H;
    if (Math.abs(dx) + Math.abs(dy) > 2) drag.current.moved = true;
    setZoom((z) => ({ ...z, tx: drag.current!.tx + dx, ty: drag.current!.ty + dy }));
  }
  function onPointerUp() {
    const moved = drag.current?.moved;
    drag.current = null;
    if (!moved && !linkFrom && !shareMode) setSelection({ kind: "none" });
  }
  function startHold(id: string) { holdTimer.current = window.setTimeout(() => openRadial(id), 480); }
  function clearHold() { if (holdTimer.current) window.clearTimeout(holdTimer.current); holdTimer.current = null; }
  const narration = useMemo(() => buildNarration(visibleNodes, allEdges), [visibleNodes, allEdges]);

  return (
    <div className={styles.wrap}>
      {/* toolbar */}
      <div className={styles.toolbar}>
        <Tabs
          items={[
            { id: "overview", label: "Overview" },
            { id: "detail", label: "Cluster detail" },
            { id: "explore", label: "Explore all" },
          ]}
          value={mode}
          onChange={(id) => onModeChange(id as Mode)}
        />
        <div className={styles.toolbarRight}>
          {hidden.size > 0 && <button type="button" className={styles.hiddenChip} onClick={() => setHidden(new Set())}><Icon name="eye" size={14} /> {hidden.size} hidden · restore</button>}
          <button type="button" className={styles.toolBtn} data-active={lens || undefined} onClick={() => { setLens((v) => !v); }}><Icon name="flask-conical" size={15} /> Lens</button>
          <button type="button" className={styles.toolBtn} data-active={comparison === "on" || undefined} onClick={() => setComparison((c) => (c === "off" ? "consent" : "off"))}><Icon name="users" size={15} /> Compare</button>
          <button type="button" className={styles.toolBtn} data-active={shareMode || undefined} onClick={() => { setShareMode((v) => !v); setShareSel(new Set()); }}><Icon name="share" size={15} /> Share</button>
          <button type="button" className={styles.toolBtn} data-active={explain || undefined} onClick={() => { setExplain((v) => !v); setSelection({ kind: "none" }); }}><Icon name="sparkles" size={15} /> Explain</button>
          <div className={styles.floorMenu}>
            <button type="button" className={styles.toolBtn} data-active={floorOpen || undefined} aria-expanded={floorOpen} onClick={() => setFloorOpen((v) => !v)}><Icon name="sliders-horizontal" size={15} /> Link strength <Icon name="chevron-down" size={13} /></button>
            {floorOpen && (
              <>
                <div className={styles.popBackdrop} onClick={() => setFloorOpen(false)} />
                <div className={styles.floorPop} role="dialog" aria-label="Link strength">
                  <span className={styles.floorPopHead}>Link strength</span>
                  <input type="range" className={styles.floor} min={1} max={6} step={1} value={floor} onChange={(e) => setFloor(Number(e.target.value))} aria-label="Link strength" />
                  <span className={styles.floorOut}>{FLOOR_LABEL[floor]}</span>
                </div>
              </>
            )}
          </div>
          <div className={styles.viewToggle} role="tablist" aria-label="View">
            <button type="button" role="tab" aria-selected={view === "graph"} className={styles.viewBtn} data-active={view === "graph" || undefined} onClick={() => setView("graph")} title="Graph view"><Icon name="git-fork" size={15} /></button>
            <button type="button" role="tab" aria-selected={view === "list"} className={styles.viewBtn} data-active={view === "list" || undefined} onClick={() => setView("list")} title="List view (text equivalent)"><Icon name="list" size={15} /></button>
          </div>
        </div>
      </div>

      {/* filters: layer toggles (link strength lives in the toolbar popover) */}
      <div className={styles.filters}>
        <div className={styles.layerChips}>
          <span className={styles.filterLabel}>Layers</span>
          {LAYERS.map((l) => (
            <button key={l.id} type="button" className={styles.layerChip} data-on={effLayers[l.id] || undefined} aria-pressed={effLayers[l.id]} disabled={l.id === "investigation" && lens} onClick={() => setLayers((p) => ({ ...p, [l.id]: !p[l.id] }))}>
              <Icon name={l.icon} size={13} /> {l.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.stage}>
        <div className={styles.canvasCol}>
          {view === "graph" && mode === "overview" && (
            <div className={styles.clusterCards}>
              {SEED_CLUSTERS.map((c) => {
                const count = visibleNodes.filter((n) => n.cluster === c.id || n.bridge?.includes(c.id)).length;
                const loops = visibleNodes.filter((n) => n.ghost && (n.cluster === c.id || n.bridge?.includes(c.id))).length;
                return (
                  <button key={c.id} type="button" className={styles.clusterCard} onClick={() => onModeChange("detail")}>
                    <span className={styles.clusterDot} style={{ background: CLUSTER_HUE[c.id] }} />
                    <span className={styles.clusterName}>{c.label}</span>
                    <span className={styles.clusterMeta}>{count} concepts{loops > 0 ? ` · ${loops} open loop` : ""}</span>
                    <span className={styles.clusterStatus} data-status={c.status}>{c.status === "active" ? "Active" : c.status === "watch" ? "Worth reviewing" : "Resolved"}</span>
                  </button>
                );
              })}
            </div>
          )}

          <div className={styles.viewport}>
            <div className={styles.bannerStack}>
              {linkFrom && <Banner icon="git-fork" tone="violet" text={`Pick another concept to link to “${nodeById[linkFrom]?.label}”.`} onCancel={() => setLinkFrom(null)} />}
              {shareMode && <Banner icon="share" tone="teal" text={`Select concepts to share — ${shareSel.size} selected.`} actionLabel={`Export ${shareSel.size} to visit packet`} onAction={() => router.push("/prepare")} onCancel={() => { setShareMode(false); setShareSel(new Set()); }} />}
              {comparison === "consent" && <ConsentBanner onAccept={() => setComparison("on")} onCancel={() => setComparison("off")} />}
            </div>
          {view === "list" ? (
            <ListView nodeById={nodeById} visibleNodes={visibleNodes} onSelect={(id) => setSelection({ kind: "node", id })} selectedId={selectedNodeId} />
          ) : (
            <div className={styles.canvas}>
              <svg
                className={styles.svg}
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
                preserveAspectRatio="xMidYMid meet"
                role="img"
                aria-label={`Whole-person health graph. ${narration}`}
                style={{ cursor: drag.current ? "grabbing" : shareMode ? "copy" : linkFrom ? "crosshair" : "grab" }}
                onWheel={onWheel}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onPointerLeave={() => (drag.current = null)}
              >
                <defs>
                  <radialGradient id="wb-glow" cx="36%" cy="30%" r="92%">
                    <stop offset="0%" stopColor="#C4B5FD" stopOpacity="0.30" />
                    <stop offset="55%" stopColor="var(--accent-soft)" stopOpacity="0.16" />
                    <stop offset="100%" stopColor="var(--bg-surface)" stopOpacity="0" />
                  </radialGradient>
                  <pattern id="wb-dots" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.5" fill="var(--fg1)" opacity="0.05" /></pattern>
                  {(Object.keys(CLUSTER_HUE) as ClusterId[]).map((id) => (
                    <radialGradient key={id} id={`sphere-${id}`} cx="34%" cy="28%" r="78%">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="0.92" />
                      <stop offset="34%" stopColor={CLUSTER_HUE[id]} stopOpacity="0.96" />
                      <stop offset="100%" stopColor={CLUSTER_DARK[id]} stopOpacity="1" />
                    </radialGradient>
                  ))}
                  <filter id="wb-soft" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#0f172a" floodOpacity="0.18" /></filter>
                  <filter id="wb-halo" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14" /></filter>
                </defs>

                <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="url(#wb-glow)" />
                <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="url(#wb-dots)" />

                <g transform={`translate(${zoom.tx},${zoom.ty}) scale(${zoom.k})`} style={{ transition: recentering ? "transform 340ms var(--wb-ease)" : "none" }}>
                  {/* concern halos (thread layer) */}
                  {effLayers.thread && SEED_CLUSTERS.map((c) => {
                    const count = visibleNodes.filter((n) => n.cluster === c.id || n.bridge?.includes(c.id)).length;
                    return (
                      <g key={c.id} opacity={c.status === "resolved" ? 0.5 : 1}>
                        <ellipse cx={c.cx} cy={c.cy} rx={c.rx} ry={c.ry} fill={CLUSTER_HUE[c.id]} opacity={0.1} filter="url(#wb-halo)" />
                        <ellipse cx={c.cx} cy={c.cy} rx={c.rx} ry={c.ry} fill="none" stroke={CLUSTER_HUE[c.id]} strokeWidth={1} strokeDasharray="2 7" opacity={0.4} />
                        {lod !== "cluster" && <><text x={c.cx} y={c.cy - c.ry + 24} textAnchor="middle" className={styles.clusterLabel} fill={CLUSTER_HUE[c.id]}>{c.label}</text><text x={c.cx} y={c.cy - c.ry + 41} textAnchor="middle" className={styles.clusterCount} fill={CLUSTER_HUE[c.id]}>{count} shown</text></>}
                      </g>
                    );
                  })}

                  {lod === "cluster" ? (
                    SEED_CLUSTERS.map((c) => {
                      const count = visibleNodes.filter((n) => n.cluster === c.id || n.bridge?.includes(c.id)).length;
                      return (
                        <g key={c.id} data-node className={styles.node} onClick={() => onModeChange("detail")}>
                          <circle cx={c.cx} cy={c.cy} r={46} fill={`url(#sphere-${c.id})`} filter="url(#wb-soft)" />
                          <text x={c.cx} y={c.cy - 2} textAnchor="middle" className={styles.blobLabel}>{c.label}</text>
                          <text x={c.cx} y={c.cy + 15} textAnchor="middle" className={styles.blobCount}>{count}</text>
                        </g>
                      );
                    })
                  ) : (
                    <>
                      {/* capture children (observation expansion, III.5) */}
                      {captureChildren.map((c) => (
                        <g key={c.id} style={{ pointerEvents: "none" }}>
                          <line x1={c.px} y1={c.py} x2={c.x} y2={c.y} stroke="#90A4AE" strokeWidth={1} strokeOpacity={0.45} strokeDasharray="2 3" />
                          <circle cx={c.x} cy={c.y} r={8} fill="var(--bg-surface)" stroke="#90A4AE" strokeWidth={1.2} />
                          <g transform={`translate(${c.x - 5}, ${c.y - 5})`}><foreignObject width="10" height="10"><span className={styles.glyph} style={{ color: "var(--fg2)" }}><Icon name="file-text" size={9} /></span></foreignObject></g>
                        </g>
                      ))}

                      {/* edges */}
                      {visibleEdges.map((e, i) => {
                        const strong = e.s >= 5;
                        const faded = (selectedNodeId && e.a !== selectedNodeId && e.b !== selectedNodeId) || (lens && e.layer !== "investigation" && !(e.a === "theory" || e.b === "theory"));
                        const isDisp = disputed.has(`${e.a}|${e.b}`);
                        const dash = e.f === "user" ? "1 7" : e.f === "conflict" || isDisp ? "8 6" : e.f === "hypothesis" ? "4 5" : e.f === "relevance" ? "2 6" : e.f === "cand" || e.s <= 3 ? "6 6" : undefined;
                        const stroke = e.lens === "against" ? "#94a3b8" : e.lens === "for" ? "#0ea5a4" : e.f === "user" ? "#8b5cf6" : e.f === "conflict" ? "#f59e0b" : e.f === "hypothesis" ? "#8b5cf6" : "#90A4AE";
                        const d = edgePath(np(e.a), np(e.b));
                        const active = !faded && (strong || hovered === e.a || hovered === e.b || e.lens === "for");
                        const touch = (id: string | null) => id && (e.a === id || e.b === id);
                        const flow = !faded && (touch(hovered) || touch(selectedNodeId));
                        return (
                          <g key={`${e.a}|${e.b}|${i}`} opacity={faded ? 0.16 : 1}>
                            {active && <path d={d} fill="none" stroke={stroke} strokeWidth={strong ? 8 : 5} strokeOpacity={0.12} strokeLinecap="round" />}
                            <path className={styles.edge} d={d} fill="none" stroke={stroke} strokeWidth={strong ? 2.8 : e.s >= 4 ? 1.9 : 1.2} strokeOpacity={isDisp ? 0.3 : strong ? 0.72 : 0.5} strokeDasharray={dash} strokeLinecap="round" onClick={(ev) => { ev.stopPropagation(); setSelection({ kind: "edge", edge: e }); }} />
                            {flow && <path className={styles.flow} d={d} fill="none" stroke={stroke} strokeLinecap="round" />}
                          </g>
                        );
                      })}

                      {/* nodes */}
                      {visibleNodes.map((n) => (
                        <NodeGlyph
                          key={n.id}
                          n={{ ...n, ...np(n.id) }}
                          childCount={deferredByAnchor[n.id] ?? 0}
                          lod={lod}
                          dim={selectedNodeId && selectedNodeId !== n.id && !neighbourIds.has(n.id) ? 0.3 : lens && n.layer !== "investigation" && !neighbourIds.has(n.id) && n.id !== "theory" ? 0.55 : 1}
                          hot={hovered === n.id || selectedNodeId === n.id}
                          selected={selectedNodeId === n.id}
                          selectedForShare={shareSel.has(n.id)}
                          expandedNode={expanded.has(n.id)}
                          onSelect={() => onNodeActivate(n.id)}
                          onContext={() => openRadial(n.id)}
                          onHoverIn={() => setHovered(n.id)}
                          onHoverOut={() => setHovered(null)}
                          onHoldStart={() => startHold(n.id)}
                          onHoldEnd={clearHold}
                        />
                      ))}
                    </>
                  )}
                </g>
              </svg>

              {radial && <RadialMenu radial={radial} onAction={runAction} onClose={() => setRadial(null)} />}

              {hoverNode && !radial && !drag.current && lod !== "cluster" && (
                <div className={styles.tooltip} style={{ left: `${((np(hoverNode.id).x * zoom.k + zoom.tx) / VIEW_W) * 100}%`, top: `${((np(hoverNode.id).y * zoom.k + zoom.ty) / VIEW_H) * 100}%` }} role="presentation">
                  <span className={styles.ttTitle}>{hoverNode.label}</span>
                  <span className={styles.ttSub}>{TYPE_LABEL[hoverNode.type]}{hoverNode.ghost ? " · awaiting result" : ` · ${hoverNode.ev} captures · ${hoverNode.last}`}</span>
                </div>
              )}

              <div className={styles.zoomControls}>
                <button type="button" className={styles.zoomBtn} aria-label="Zoom in" title="Zoom in" onClick={() => setZoom((z) => ({ ...z, k: Math.min(2.6, z.k * 1.2) }))}><Icon name="plus" size={15} /></button>
                <button type="button" className={styles.zoomBtn} aria-label="Zoom out" title="Zoom out" onClick={() => setZoom((z) => ({ ...z, k: Math.max(0.4, z.k * 0.83) }))}><Icon name="chevron-down" size={15} /></button>
                <button type="button" className={styles.zoomBtn} aria-label="Recenter map" title="Recenter to default view" onClick={recenter}><Icon name="home" size={15} /></button>
                <button type="button" className={styles.zoomBtn} data-saved={homeSaved || undefined} aria-label="Set current view as default" title="Set current view as default" onClick={saveHome}><Icon name={homeSaved ? "check" : "star"} size={15} /></button>
              </div>
              <div className={styles.lodHint}>{lod === "cluster" ? "Concern overview" : lod === "detail" ? "Detail — evidence" : "Concepts"}{lens ? " · investigation lens" : ""}</div>
              <div className={styles.scrubDock}>
                <Icon name="clock" size={13} />
                <div className={styles.scrubTrack}>
                  <div className={styles.scrubLine} />
                  <div className={styles.scrubFill} style={{ width: `calc((100% - 16px) * ${scrub / 5})` }} />
                  {WEEK_LABELS.map((m, i) => (
                    <span key={m} className={styles.scrubTickMark} data-on={i <= scrub || undefined} style={{ left: `calc(8px + (100% - 16px) * ${i / 5})` }} />
                  ))}
                  <span className={styles.scrubHandle} style={{ left: `calc(8px + (100% - 16px) * ${scrub / 5})` }} />
                  <input type="range" className={styles.scrubA11y} min={0} max={5} step={1} value={scrub} onChange={(e) => setScrub(Number(e.target.value))} aria-label="Replay timeline" aria-valuetext={scrub >= 5 ? "June 2026, all time" : `As of ${WEEK_LABELS[scrub]} 2026`} />
                  <div className={styles.scrubTicks} aria-hidden="true">
                    {WEEK_LABELS.map((m, i) => (
                      <span key={m} className={styles.scrubTick} data-on={i <= scrub || undefined} style={{ left: `calc(8px + (100% - 16px) * ${i / 5})` }}>{m}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          </div>

          {view === "graph" && <Legend lens={lens} />}
        </div>

        <aside className={styles.inspector} aria-live="polite">
          {explain ? (
            <ExplainPanel narration={narration} onClose={() => setExplain(false)} />
          ) : selection.kind === "node" && nodeById[selection.id] ? (
            <NodePanel node={nodeById[selection.id]!} edges={allEdges} nodeById={nodeById} floor={floor} showWeak={showWeak} evidenceAll={evidenceAll} expandedNode={expanded.has(selection.id)} expandable={Boolean(nodeById[selection.id]?.captures) || (deferredByAnchor[selection.id] ?? 0) > 0} onAction={runAction} onSelectNeighbour={(id) => setSelection({ kind: "node", id })} onShowWeak={() => { setShowWeak(true); setFloor(1); }} onToggleEvidence={() => setEvidenceAll((v) => !v)} onToggleExpand={() => setExpanded((prev) => { const n = new Set(prev); n.has(selection.id) ? n.delete(selection.id) : n.add(selection.id); return n; })} />
          ) : selection.kind === "edge" ? (
            <EdgePanel edge={selection.edge} nodeById={nodeById} disputed={disputed.has(`${selection.edge.a}|${selection.edge.b}`)} onDispute={() => setDisputed((p) => new Set(p).add(`${selection.edge.a}|${selection.edge.b}`))} />
          ) : (
            <OverviewPanel conceptCount={conceptCount} openLoopCount={openLoopCount} clusterCount={SEED_CLUSTERS.length} />
          )}
        </aside>
      </div>
    </div>
  );
}

/* ---------- SVG node ---------- */
function NodeGlyph({ n, lod, dim, hot, selected, selectedForShare, expandedNode, childCount, onSelect, onContext, onHoverIn, onHoverOut, onHoldStart, onHoldEnd }: {
  n: GraphNode; lod: "cluster" | "concept" | "detail"; dim: number; hot: boolean; selected: boolean; selectedForShare: boolean; expandedNode: boolean; childCount: number;
  onSelect: () => void; onContext: () => void; onHoverIn: () => void; onHoverOut: () => void; onHoldStart: () => void; onHoldEnd: () => void;
}) {
  const theory = n.lensRole === "theory";
  const ext = n.type === "external";
  const cid: ClusterId = (n.bridge && n.bridge[0]) || n.cluster || "head";
  const hue = theory || ext ? (theory ? "#8b5cf6" : "#64748b") : CLUSTER_HUE[cid];
  const r = (theory ? 17 : 14) + Math.min(n.ev, 14) * 0.42;
  const expandable = childCount > 0 && !expandedNode;
  const label = `${n.label}, ${TYPE_LABEL[n.type]}, ${n.ev} captures, last ${n.last}${expandable ? `, expandable — ${childCount} related items hidden` : ""}`;
  return (
    <g
      data-node
      tabIndex={0}
      role="button"
      aria-label={label}
      className={styles.node}
      opacity={dim}
      onClick={(e) => { e.stopPropagation(); onSelect(); }}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } if (e.key === "ContextMenu") { e.preventDefault(); onContext(); } }}
      onContextMenu={(e) => { e.preventDefault(); onContext(); }}
      onMouseEnter={onHoverIn}
      onMouseLeave={onHoverOut}
      onPointerDown={onHoldStart}
      onPointerUp={onHoldEnd}
      onPointerLeave={onHoldEnd}
    >
      <circle cx={n.x} cy={n.y} r={r + 6} fill="none" stroke={hue} strokeOpacity={0.22} strokeWidth={Math.max(1.2, n.ev / 3.5)} />
      {(hot || selectedForShare) && <circle cx={n.x} cy={n.y} r={r + 12} fill="none" stroke={selectedForShare ? "#0ea5a4" : hue} strokeWidth={selectedForShare ? 2.4 : 1.4} opacity={0.6} strokeDasharray={selectedForShare ? "4 3" : undefined} />}
      {expandedNode && <circle cx={n.x} cy={n.y} r={r + 3} fill="none" stroke={hue} strokeWidth={1} opacity={0.4} />}
      {selected && <circle key="ripple" className={styles.ripple} cx={n.x} cy={n.y} r={r} fill="none" stroke={hue} strokeWidth={2} />}

      {n.aggregate ? (
        <circle cx={n.x} cy={n.y} r={r} fill="var(--bg-subtle)" stroke="#94a3b8" strokeWidth={1.6} strokeDasharray="2 3" opacity={0.85} />
      ) : n.ghost ? (
        <circle cx={n.x} cy={n.y} r={r} fill="var(--bg-surface)" stroke={hue} strokeWidth={1.8} strokeDasharray="3 3" filter="url(#wb-soft)" />
      ) : theory ? (
        <rect x={n.x - r} y={n.y - r} width={r * 2} height={r * 2} rx={6} transform={`rotate(45 ${n.x} ${n.y})`} fill={`url(#sphere-sleep)`} filter="url(#wb-soft)" opacity={0.9} />
      ) : n.bridge && n.bridge.length >= 2 ? (
        // bridge node: one pie wedge per concern, so it belongs to ALL of them
        <g filter="url(#wb-soft)" opacity={0.45 + n.act * 0.55}>
          {n.bridge.length === 2 ? (
            <>
              <circle cx={n.x} cy={n.y} r={r} fill={`url(#sphere-${n.bridge[0]})`} />
              <path d={`M${n.x},${n.y - r} A${r},${r} 0 0 1 ${n.x},${n.y + r} Z`} fill={`url(#sphere-${n.bridge[1]})`} />
            </>
          ) : (
            n.bridge.map((cl, i) => (
              <path key={cl} d={wedgePath(n.x, n.y, r, i, n.bridge!.length)} fill={`url(#sphere-${cl})`} stroke="var(--bg-surface)" strokeWidth={1.4} />
            ))
          )}
          {n.bridge.length === 2 && <line x1={n.x} y1={n.y - r} x2={n.x} y2={n.y + r} stroke="var(--bg-surface)" strokeWidth={1.5} opacity={0.85} />}
        </g>
      ) : (
        <circle cx={n.x} cy={n.y} r={r} fill={`url(#sphere-${cid})`} filter="url(#wb-soft)" opacity={0.45 + n.act * 0.55} />
      )}
      {!n.ghost && !n.aggregate && <ellipse cx={n.x - r * 0.32} cy={n.y - r * 0.4} rx={r * 0.42} ry={r * 0.28} fill="#fff" opacity={0.32} />}

      <g transform={`translate(${n.x - 7}, ${n.y - 7})`} style={{ pointerEvents: "none" }}>
        <foreignObject width="14" height="14"><span className={styles.glyph} style={{ color: n.ghost || n.aggregate ? hue : "#fff" }}><Icon name={TYPE_ICON[n.type]} size={13} /></span></foreignObject>
      </g>

      {n.pinned && <g transform={`translate(${n.x + r - 3}, ${n.y - r - 1})`} style={{ pointerEvents: "none" }}><circle r="7.5" fill="var(--bg-surface)" stroke={hue} strokeWidth="1" /><foreignObject x="-6" y="-6" width="12" height="12"><span className={styles.glyph} style={{ color: hue }}><Icon name="star" size={10} /></span></foreignObject></g>}
      {n.ghost && <g transform={`translate(${n.x - r - 1}, ${n.y - r - 1})`} style={{ pointerEvents: "none" }}><circle r="7.5" fill="var(--warning-soft)" stroke={hue} strokeWidth="1" /><foreignObject x="-6" y="-6" width="12" height="12"><span className={styles.glyph} style={{ color: "#b45309" }}><Icon name="clock" size={10} /></span></foreignObject></g>}
      {expandable && (
        <g className={styles.orbit} style={{ pointerEvents: "none" }}>
          <circle cx={n.x} cy={n.y} r={r + 9} fill="none" stroke={hue} strokeWidth="1" strokeDasharray="1.5 5" opacity="0.45" />
          {Array.from({ length: Math.min(childCount, 6) }).map((_, i) => {
            const total = Math.min(childCount, 6);
            const a = -Math.PI / 2 + (i / total) * Math.PI * 2;
            const rr = r + 9;
            return <circle key={i} cx={n.x + Math.cos(a) * rr} cy={n.y + Math.sin(a) * rr} r="2.6" fill={hue} opacity="0.7" />;
          })}
        </g>
      )}

      <text className={styles.nodeLabel} x={n.x} y={n.y + r + 16} textAnchor="middle">{n.label}</text>
      {n.ghost && <text className={styles.ghostLabel} x={n.x} y={n.y + r + 30} textAnchor="middle" fill={hue}>open loop</text>}
      {n.aggregate && <text className={styles.ghostLabel} x={n.x} y={n.y + r + 30} textAnchor="middle" fill="#64748b">others also track</text>}
      {lod === "detail" && !n.ghost && !n.aggregate && <text className={styles.nodeMeta} x={n.x} y={n.y + r + 30} textAnchor="middle">{n.ev} captures · {n.last}</text>}
    </g>
  );
}

function wedgePath(cx: number, cy: number, r: number, i: number, total: number) {
  const a0 = -Math.PI / 2 + (i / total) * Math.PI * 2;
  const a1 = -Math.PI / 2 + ((i + 1) / total) * Math.PI * 2;
  const p0x = cx + r * Math.cos(a0), p0y = cy + r * Math.sin(a0);
  const p1x = cx + r * Math.cos(a1), p1y = cy + r * Math.sin(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${cx},${cy} L${p0x.toFixed(1)},${p0y.toFixed(1)} A${r},${r} 0 ${large} 1 ${p1x.toFixed(1)},${p1y.toFixed(1)} Z`;
}

function edgePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const bow = Math.min(46, len * 0.13);
  return `M${a.x},${a.y} Q${(mx + (-dy / len) * bow).toFixed(1)},${(my + (dx / len) * bow).toFixed(1)} ${b.x},${b.y}`;
}

/* ---------- radial menu ---------- */
function RadialMenu({ radial, onAction, onClose }: { radial: { id: string; xPct: number; yPct: number }; onAction: (a: string, id: string) => void; onClose: () => void }) {
  const radius = 82;
  return (
    <div className={styles.radialWrap} onClick={onClose}>
      <div className={styles.radial} style={{ left: `${radial.xPct}%`, top: `${radial.yPct}%` }}>
        <span className={styles.radialCenter}><Icon name="git-fork" size={15} /></span>
        {NODE_ACTIONS.map((a, idx) => {
          const ang = -Math.PI / 2 + (idx / NODE_ACTIONS.length) * Math.PI * 2;
          return (
            <button key={a.id} type="button" className={styles.radialBtn} style={{ transform: `translate(${Math.cos(ang) * radius}px, ${Math.sin(ang) * radius}px)` }} title={a.label} aria-label={a.label} onClick={(e) => { e.stopPropagation(); onAction(a.id, radial.id); }}>
              <Icon name={a.icon} size={16} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- banners ---------- */
function Banner({ icon, tone, text, actionLabel, onAction, onCancel }: { icon: string; tone: "violet" | "teal"; text: string; actionLabel?: string; onAction?: () => void; onCancel: () => void }) {
  return (
    <div className={styles.banner} data-tone={tone}>
      <Icon name={icon} size={15} />
      <span className={styles.bannerText}>{text}</span>
      {actionLabel && <Button variant="primary" size="sm" onClick={onAction}>{actionLabel}</Button>}
      <button type="button" className={styles.bannerCancel} onClick={onCancel} aria-label="Cancel"><Icon name="x" size={15} /></button>
    </div>
  );
}
function ConsentBanner({ onAccept, onCancel }: { onAccept: () => void; onCancel: () => void }) {
  return (
    <div className={styles.banner} data-tone="violet">
      <Icon name="shield-check" size={15} />
      <span className={styles.bannerText}>Comparison is <strong>opt-in and aggregate-only</strong> — “people with a similar pattern often also tracked…”. Never identifies anyone, never shared with your clinic or employer.</span>
      <Button variant="primary" size="sm" onClick={onAccept}>Turn on</Button>
      <button type="button" className={styles.bannerCancel} onClick={onCancel} aria-label="Cancel"><Icon name="x" size={15} /></button>
    </div>
  );
}

/* ---------- inspector panels ---------- */
function OverviewPanel({ conceptCount, openLoopCount, clusterCount }: { conceptCount: number; openLoopCount: number; clusterCount: number }) {
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="git-fork" size={16} /></span><div><p className={styles.inspTitleSerif}>Your whole-person map</p><p className={styles.inspSub}>Scoped to you · traceable to its sources</p></div></div>
      <div className={styles.statRow}>
        <div className={styles.stat}><span className={styles.statValue}>{clusterCount}</span><span className={styles.statLabel}>concerns</span></div>
        <div className={styles.stat}><span className={styles.statValue}>{conceptCount}</span><span className={styles.statLabel}>concepts</span></div>
        <div className={styles.stat}><span className={styles.statValue}>{openLoopCount}</span><span className={styles.statLabel}>open loops</span></div>
      </div>
      <p className={styles.inspBody}>Tap a <strong>node</strong> to expand its captures and act on it. Tap a <strong>line</strong> for why two items connect. Right-click or long-press for quick actions. <span className={styles.bridgeName}>Dizziness</span> bridges Headaches and Sleep.</p>
      <p className={styles.tipLine}><Icon name="search" size={13} /> Scroll to zoom · drag to pan · use Layers, Lens, Replay and State to explore the full model.</p>
      <div className={styles.safety}><Icon name="shield-check" size={14} /><span>This map shows how items appear in your records — not medical severity. Lines show recorded relationships, not proof of cause.</span></div>
    </>
  );
}

function ExplainPanel({ narration, onClose }: { narration: string; onClose: () => void }) {
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="sparkles" size={16} /></span><div><p className={styles.inspTitle}>Explain my graph</p><p className={styles.inspSub}>Plain-language, source-cited</p></div></div>
      <p className={styles.inspBody}>{narration}</p>
      <div className={styles.safety}><Icon name="info" size={14} /><span>This narration describes what's in your records in plain language. It doesn't diagnose or claim cause.</span></div>
      <Button variant="ghost" icon="x" onClick={onClose}>Close narration</Button>
    </>
  );
}

function NodePanel({ node, edges, nodeById, floor, showWeak, evidenceAll, expandedNode, expandable, onAction, onSelectNeighbour, onShowWeak, onToggleEvidence, onToggleExpand }: {
  node: GraphNode; edges: GraphEdge[]; nodeById: Record<string, GraphNode>; floor: number; showWeak: boolean; evidenceAll: boolean; expandedNode: boolean; expandable: boolean;
  onAction: (a: string, id: string) => void; onSelectNeighbour: (id: string) => void; onShowWeak: () => void; onToggleEvidence: () => void; onToggleExpand: () => void;
}) {
  const hue = node.lensRole === "theory" ? "#8b5cf6" : node.type === "external" ? "#64748b" : CLUSTER_HUE[(node.bridge && node.bridge[0]) || node.cluster || "head"];
  const membership = node.bridge ? node.bridge.map(clusterLabel) : node.cluster ? [clusterLabel(node.cluster)] : [TYPE_LABEL[node.type]];
  const related = edges
    .map((e) => (e.a === node.id ? { id: e.b, e } : e.b === node.id ? { id: e.a, e } : null))
    .filter((x): x is { id: string; e: GraphEdge } => x !== null && Boolean(nodeById[x.id]))
    .sort((p, q) => q.e.s - p.e.s);
  const shown = related.filter((r) => r.e.s >= floor || r.e.f === "user").slice(0, 12);
  const hiddenCount = Math.max(node.relatedTotal - shown.length, 0);
  const captures = node.captures ?? node.sources.map((s, i) => ({ source: s, text: `Source-linked ${sourceLabel(s)} mentioning ${node.label.toLowerCase()}.`, date: `#${i + 1}` }));
  const capsShown = evidenceAll ? captures : captures.slice(0, 3);

  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge} style={{ background: `${hue}1f`, color: hue }}><Icon name={TYPE_ICON[node.type]} size={16} /></span><div><p className={styles.inspTitle}>{node.label}</p><p className={styles.inspSub}>{TYPE_LABEL[node.type]}</p></div></div>
      <div className={styles.chipRow}>
        {membership.map((m) => <Chip key={m} tone="neutral" size="sm" dot>{m}</Chip>)}
        {node.bridge && <Chip tone="violet" size="sm" icon="git-fork">Bridge</Chip>}
        {node.pinned && <Chip tone="amber" size="sm" icon="star">Pinned</Chip>}
        {node.aggregate && <Chip tone="neutral" size="sm" icon="users">Aggregate</Chip>}
      </div>

      {node.aggregate ? (
        <div className={styles.conflictNote}><Icon name="users" size={14} /><span>An opt-in, aggregate pattern from people with similar records — not from your data, and not a recommendation.</span></div>
      ) : node.ghost ? (
        <div className={styles.openLoopNote}><Icon name="clock" size={14} /><span>Awaiting result — worth a follow-up. Not an alarm.</span></div>
      ) : (
        <>
          <div className={styles.section}>
            <div className={styles.sectionHead}><span>Related</span><span className={styles.sectionCount}>Showing {shown.length} of {node.relatedTotal}</span></div>
            <ul className={styles.neighList}>
              {shown.map((r) => { const nb = nodeById[r.id]!; const fam = FAMILY[r.e.f]; return (
                <li key={r.id}><button type="button" className={styles.neighRow} onClick={() => onSelectNeighbour(r.id)}><span className={styles.neighDot} style={{ background: nb.type === "external" ? "#64748b" : CLUSTER_HUE[(nb.bridge && nb.bridge[0]) || nb.cluster || "head"] }} /><span className={styles.neighName}>{nb.label}</span><span className={styles.neighFam} data-fam={r.e.f}>{fam.label}</span></button></li>
              ); })}
            </ul>
            {hiddenCount > 0 && !showWeak && <Button variant="tertiary" size="sm" icon="plus" onClick={onShowWeak}>Show {hiddenCount} weaker link{hiddenCount > 1 ? "s" : ""}</Button>}
          </div>

          <div className={styles.section}>
            <div className={styles.sectionHead}><span>Evidence</span><ConfidenceDots level={node.conf} label={`${node.ev} captures`} /></div>
            <ul className={styles.capList}>{capsShown.map((c, i) => <li key={i} className={styles.capRow}><SourceChip type={c.source} /><span className={styles.capText}>{c.text}</span><span className={styles.capDate}>{c.date}</span></li>)}</ul>
            <div className={styles.evRow}>
              {captures.length > 3 && <Button variant="tertiary" size="sm" icon={evidenceAll ? "chevron-down" : "file-text"} onClick={onToggleEvidence}>{evidenceAll ? "Show fewer" : `Complete evidence mode (${captures.length})`}</Button>}
              {expandable && <Button variant="tertiary" size="sm" icon="git-fork" onClick={onToggleExpand}>{expandedNode ? "Collapse on map" : "Expand on map"}</Button>}
            </div>
          </div>
        </>
      )}

      <div className={styles.metaBlock}>
        <div className={styles.metaRow}><span className={styles.metaKey}>First noted</span><span className={styles.metaVal}>{node.first}</span></div>
        <div className={styles.metaRow}><span className={styles.metaKey}>Last activity</span><span className={styles.metaVal}>{node.last}</span></div>
      </div>

      <div className={styles.actionList}>{NODE_ACTIONS.map((a) => <button key={a.id} type="button" className={styles.action} data-danger={a.id === "hide" || undefined} onClick={() => onAction(a.id, node.id)}><Icon name={a.icon} size={15} /> {a.label}</button>)}</div>
    </>
  );
}

function EdgePanel({ edge, nodeById, disputed, onDispute }: { edge: GraphEdge; nodeById: Record<string, GraphNode>; disputed: boolean; onDispute: () => void }) {
  const a = nodeById[edge.a];
  const b = nodeById[edge.b];
  const fam = FAMILY[edge.f];
  const strengthLabel = edge.s >= 5 ? "Well-supported in your records" : edge.s >= 4 ? "Some support in your records" : "Candidate — weak or system-inferred";
  const dots = Math.max(1, Math.round((edge.s / 7) * 5));
  const allSources = Array.from(new Set([...(a?.sources ?? []), ...(b?.sources ?? [])]));
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="share" size={16} /></span><div><p className={styles.inspTitle}>Why connected?</p><p className={styles.inspSub}>{a?.label} · {b?.label}</p></div></div>
      <div className={styles.chipRow}><Chip tone={fam.tone} size="sm">{fam.label}</Chip>{edge.lens && <Chip tone={edge.lens === "for" ? "tealmid" : "neutral"} size="sm">Evidence {edge.lens}</Chip>}{disputed && <Chip tone="amber" size="sm" icon="alert-triangle">Disputed</Chip>}</div>
      <p className={styles.inspBody}>{fam.note}</p>
      {edge.f === "conflict" && <div className={styles.conflictNote}><Icon name="alert-triangle" size={14} /><span>Both sources are kept. WellBe shows the disagreement rather than resolving it for you.</span></div>}
      <div className={styles.metaBlock}><div className={styles.metaRow}><span className={styles.metaKey}>Evidence strength</span><ConfidenceDots level={dots} label={strengthLabel} /></div><div className={styles.sourceRow}>{allSources.map((s) => <SourceChip key={s} type={s} />)}</div></div>
      <div className={styles.safety}><Icon name="info" size={14} /><span>This means these items were related in your records in the way shown above. It does not prove that one caused the other.</span></div>
      {!disputed && edge.f !== "user" && <Button variant="ghost" full icon="x-circle" onClick={onDispute}>Dispute this connection</Button>}
    </>
  );
}

/* ---------- list / timeline equivalent ---------- */
function ListView({ nodeById, visibleNodes, onSelect, selectedId }: { nodeById: Record<string, GraphNode>; visibleNodes: GraphNode[]; onSelect: (id: string) => void; selectedId: string | null }) {
  const vis = new Set(visibleNodes.map((n) => n.id));
  return (
    <div className={styles.listView}>
      {SEED_CLUSTERS.map((c) => {
        const nodes = visibleNodes.filter((n) => n.cluster === c.id || n.bridge?.includes(c.id));
        if (!nodes.length) return null;
        return (
          <section key={c.id} className={styles.listSection}>
            <header className={styles.listSectionHead}><span className={styles.clusterDot} style={{ background: CLUSTER_HUE[c.id] }} /><span className={styles.listSectionName}>{c.label}</span><span className={styles.listSectionMeta}>{nodes.length} concepts</span></header>
            <ul className={styles.listRows}>
              {nodes.map((n) => (
                <li key={n.id}><button type="button" className={styles.listRow} data-active={selectedId === n.id || undefined} onClick={() => onSelect(n.id)}>
                  <span className={styles.listIcon} style={{ color: CLUSTER_HUE[c.id] }}><Icon name={TYPE_ICON[n.type]} size={15} /></span>
                  <span className={styles.listRowMain}><span className={styles.listRowName}>{n.label}{n.bridge && <span className={styles.bridgeTag}>bridge</span>}</span><span className={styles.listRowSub}>{TYPE_LABEL[n.type]} · last {n.last}</span></span>
                  {n.ghost ? <span className={styles.loopTag}><Icon name="clock" size={12} /> open loop</span> : <ConfidenceDots level={n.conf} label={`${n.ev} captures`} />}
                </button></li>
              ))}
            </ul>
          </section>
        );
      })}
      {!vis.size && <p className={styles.inspBody}>Nothing matches the current filters.</p>}
    </div>
  );
}

function Legend({ lens }: { lens: boolean }) {
  return (
    <div className={styles.legend}>
      <span className={styles.legendGroup}>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="circle" /> Symptom</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="square" /> Context</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="diamond" /> Lab / theory</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="bridge" /> Bridges concerns</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="ghost" /> Open loop</span>
      </span>
      <span className={styles.legendGroup}>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="strong" /> Strong</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="dashed" /> Candidate</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="user" /> You linked</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="conflict" /> Conflicting</span>
        {lens && <span className={styles.legendItem}><span className={styles.lLine} data-kind="for" /> Evidence for / against</span>}
      </span>
    </div>
  );
}

function buildNarration(nodes: GraphNode[], edges: GraphEdge[]): string {
  const clusters = SEED_CLUSTERS.filter((c) => nodes.some((n) => n.cluster === c.id || n.bridge?.includes(c.id)));
  if (!clusters.length) return "Your map is empty — add a capture to begin.";
  const loops = nodes.filter((n) => n.ghost);
  const bridges = nodes.filter((n) => n.bridge);
  const parts: string[] = [];
  parts.push(`You're carrying ${clusters.length} concern${clusters.length > 1 ? "s" : ""}: ${clusters.map((c) => `${c.label} (${c.status === "watch" ? "worth reviewing" : c.status})`).join(", ")}.`);
  if (bridges.length) parts.push(`${bridges.map((b) => b.label).join(" and ")} appear${bridges.length > 1 ? "" : "s"} across more than one concern, so ${bridges.length > 1 ? "they" : "it"} bridge${bridges.length > 1 ? "" : "s"} them in your records.`);
  if (loops.length) parts.push(`${loops.length} open loop${loops.length > 1 ? "s are" : " is"} worth chasing: ${loops.map((l) => l.label).join(", ")}.`);
  parts.push("These are patterns recorded in your own sources — not a diagnosis or a claim of cause.");
  return parts.join(" ");
}
