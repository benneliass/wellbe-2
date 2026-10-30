/*
 * Moving nodes on the cockpit map: pointer math, the click-vs-drag threshold,
 * keyboard nudges, and per-patient persistence of the positions a person chose.
 */


export { passedThreshold, arrowDelta, clientToSvg, svgToGraph, dragTo, DRAG_THRESHOLD_PX, KEY_STEP, KEY_STEP_BIG } from "@wellbe/ui/map/core";
export type { Positions, Zoom } from "@wellbe/ui/map/core";
import type { Positions } from "@wellbe/ui/map/core";

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
