import type { Point as Pt, MapPositions, MapCamera } from "./types";
import { MAP_INTERACTION } from "./config";

/** Screen pixels a pointer must travel before a press becomes a drag (below it, it's a click). */
export const DRAG_THRESHOLD_PX = MAP_INTERACTION.dragThresholdPx;
export const KEY_STEP = MAP_INTERACTION.keyStep;
export const KEY_STEP_BIG = MAP_INTERACTION.bigKeyStep;

/** Graph-space positions keyed by node id, or `cluster:<id>` for a concern title. */
export type Positions = MapPositions;

export type Zoom = MapCamera;

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
