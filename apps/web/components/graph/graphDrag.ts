/*
 * Moving nodes on the cockpit map: pointer math, the click-vs-drag threshold,
 * keyboard nudges, and per-patient persistence of the positions a person chose.
 */

import type { Pt } from "./liveGraphLayout";

/** Screen pixels a pointer must travel before a press becomes a drag (below it, it's a click). */
export const DRAG_THRESHOLD_PX = 4;
export const KEY_STEP = 8;
export const KEY_STEP_BIG = 40;

/** Graph-space positions keyed by node id, or `cluster:<id>` for a concern title. */
export type Positions = Record<string, Pt>;

export interface Zoom {
  k: number;
  tx: number;
  ty: number;
}

export function passedThreshold(dx: number, dy: number, threshold = DRAG_THRESHOLD_PX): boolean {
  return Math.hypot(dx, dy) >= threshold;
}

/** Client (screen) point -> SVG user space, honouring viewBox scaling and letterboxing. */
export function clientToSvg(svg: SVGSVGElement, clientX: number, clientY: number, view: { width: number; height: number }): Pt {
  const ctm = typeof svg.getScreenCTM === "function" ? svg.getScreenCTM() : null;
  if (ctm) {
    const inv = ctm.inverse();
    return { x: inv.a * clientX + inv.c * clientY + inv.e, y: inv.b * clientX + inv.d * clientY + inv.f };
  }
  const r = svg.getBoundingClientRect();
  return { x: ((clientX - r.left) / (r.width || view.width)) * view.width, y: ((clientY - r.top) / (r.height || view.height)) * view.height };
}

/** SVG user space -> graph space, undoing the current pan/zoom transform. */
export function svgToGraph(p: Pt, zoom: Zoom): Pt {
  return { x: (p.x - zoom.tx) / zoom.k, y: (p.y - zoom.ty) / zoom.k };
}

/** Every dragged item keeps its offset from where the drag started. */
export function dragTo(start: Positions, delta: Pt): Positions {
  const out: Positions = {};
  for (const [id, p] of Object.entries(start)) out[id] = { x: Math.round((p.x + delta.x) * 10) / 10, y: Math.round((p.y + delta.y) * 10) / 10 };
  return out;
}

export function arrowDelta(key: string, big: boolean): Pt | null {
  const s = big ? KEY_STEP_BIG : KEY_STEP;
  if (key === "ArrowLeft") return { x: -s, y: 0 };
  if (key === "ArrowRight") return { x: s, y: 0 };
  if (key === "ArrowUp") return { x: 0, y: -s };
  if (key === "ArrowDown") return { x: 0, y: s };
  return null;
}

export function positionsKey(patientId: string): string {
  return `wellbe.graph.positions.${patientId}`;
}

type Stored = Record<string, Record<string, [number, number]>>;

function read(patientId: string): Stored {
  try {
    const raw = window.localStorage.getItem(positionsKey(patientId));
    const parsed = raw ? (JSON.parse(raw) as unknown) : null;
    return parsed && typeof parsed === "object" ? (parsed as Stored) : {};
  } catch {
    return {};
  }
}

/** Positions saved for this patient and view, dropping ids that are no longer on the map. */
export function loadPositions(patientId: string, viewKey: string, validIds: ReadonlySet<string>): Positions {
  const out: Positions = {};
  const saved = read(patientId)[viewKey];
  if (!saved || typeof saved !== "object") return out;
  for (const [id, p] of Object.entries(saved)) {
    if (!validIds.has(id) || !Array.isArray(p)) continue;
    const [x, y] = p;
    if (Number.isFinite(x) && Number.isFinite(y)) out[id] = { x, y };
  }
  return out;
}

/** Writes this view's positions; an empty set removes them (and the key once nothing is left). */
export function savePositions(patientId: string, viewKey: string, positions: Positions): void {
  try {
    const all = read(patientId);
    const entries = Object.entries(positions);
    if (entries.length) all[viewKey] = Object.fromEntries(entries.map(([id, p]) => [id, [p.x, p.y]]));
    else delete all[viewKey];
    if (Object.keys(all).length) window.localStorage.setItem(positionsKey(patientId), JSON.stringify(all));
    else window.localStorage.removeItem(positionsKey(patientId));
  } catch {
    // Storage full or blocked: the positions just don't survive a reload.
  }
}
