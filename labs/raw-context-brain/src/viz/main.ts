import { Graph } from "@cosmos.gl/graph";
import { loadCasePeople, labFromCase } from "../cases.js";
import { RELATION_LABEL, arrivalName, independenceName, sourceName } from "../relation.js";
import { RawContextLab } from "../router.js";
const stage = required(document.querySelector<HTMLDivElement>("#stage"));
const degreeLabels = required(document.querySelector<HTMLElement>("#degree-labels"));
const noteFacts = required(document.querySelector<HTMLElement>("#note-facts"));
const assessments = required(document.querySelector<HTMLElement>("#assessments"));
const storeButton = required(document.querySelector<HTMLButtonElement>("#store"));
const peopleNav = required(document.querySelector<HTMLElement>("#people"));
const noteAdd = required(document.querySelector<HTMLElement>("#note-add"));
const notePop = required(document.querySelector<HTMLFormElement>("#capture"));
const newNoteButton = required(document.querySelector<HTMLButtonElement>("#new-note"));
const suggestStatus = required(document.querySelector<HTMLElement>("#suggest-status"));
const source = required(document.querySelector<HTMLElement>("#source"));
const capture = required(document.querySelector<HTMLFormElement>("#capture"));
const noteInput = required(document.querySelector<HTMLTextAreaElement>("#note"));
const resetButton = required(document.querySelector<HTMLButtonElement>("#reset"));

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    if (char === "&") return "&amp;";
    if (char === "<") return "&lt;";
    if (char === ">") return "&gt;";
    if (char === '"') return "&quot;";
    return "&#39;";
  });
}

function required<T>(value: T | null): T {
  if (value === null) throw new Error("lab page is missing a required element");
  return value;
}

const SPACE_SIZE = 4096;
const CONNECTOR_LINK: [number, number, number, number] = [0.82, 0.86, 0.9, 0.78];
const FAINT_LINK: [number, number, number, number] = [0.82, 0.86, 0.9, 0.22];
const MAP_LINK: [number, number, number, number] = [0.82, 0.86, 0.9, 0.16];
const KIND_RGB: Record<string, [number, number, number]> = {
  note: [0.93, 0.62, 0.22],
  lab_text: [0.33, 0.58, 0.9],
  image_caption: [0.35, 0.78, 0.48],
  pdf_extract: [0.72, 0.42, 0.82],
  hub: [0.62, 0.66, 0.7],
};

let personId = "";
let lab = new RawContextLab({ seed: 7, pageSize: 1, hopLimit: 24, expansionBudget: 400 });
let positions = layout(lab.view(personId));
let graph: Graph | null = null;
let selectedId: string | null = null;
let showAll = true;
/** Notes opened in this look, in click order. The last one is the note left open in the panel. */
let trail: string[] = [];
const openBlocks = new Set<string>();
let drawnIds: string[] = [];
let labelState: Array<{ id: string; x: number; y: number; degree: number; size: number }> = [];

function layout(view: { nodes: Array<{ degree: number }>; links: Array<{ source: number; target: number }> }): Float32Array {
  const count = view.nodes.length;
  const pos = new Float32Array(count * 2);
  const order = view.nodes
    .map((node, index) => ({ index, degree: node.degree }))
    .sort((left, right) => right.degree - left.degree || left.index - right.index);
  // Small dossiers sit on a short step. Past 400 notes the step stays wider so the spiral does not fall into one pile.
  const spacing = count > 400 ? 68 : 42;
  const core = Math.min(4, order.filter((item) => item.degree >= 30).length);
  order.forEach((item, rank) => {
    const wobble = ((item.index * 0.618) % 1) - 0.5;
    const inCore = rank < core && core > 0;
    const radius = inCore
      ? spacing * 1.7
      : Math.sqrt(Math.max(rank - core, 0)) * spacing * (1 + wobble * 0.12);
    const angle = inCore
      ? (rank / core) * Math.PI * 2 + wobble * 0.25
      : rank * 2.399963 + wobble * 0.55;
    pos[item.index * 2] = Math.cos(angle) * radius;
    pos[item.index * 2 + 1] = Math.sin(angle) * radius;
  });
  return pos;
}

const CIRCLE_MIN = 16;
const CIRCLE_MAX = 50;

// Link count in this view maps onto the circle scale. The fewest links sit at
// the small end and the most links at the large end. Equal counts share a size.
// A difference of one link stays a different size, so this does not round.
function circleSizes(degrees: ArrayLike<number>): Float32Array {
  const count = degrees.length;
  const sizes = new Float32Array(count);
  if (count === 0) return sizes;
  let lowest = Infinity;
  let highest = -Infinity;
  for (let index = 0; index < count; index += 1) {
    const degree = degrees[index] ?? 0;
    if (degree < lowest) lowest = degree;
    if (degree > highest) highest = degree;
  }
  const span = highest - lowest;
  const mid = (CIRCLE_MIN + CIRCLE_MAX) / 2;
  for (let index = 0; index < count; index += 1) {
    const degree = degrees[index] ?? 0;
    sizes[index] = span === 0 ? mid : CIRCLE_MIN + ((degree - lowest) / span) * (CIRCLE_MAX - CIRCLE_MIN);
  }
  return sizes;
}

// Cosmos simulationCollision treats a circle's pixel size as a map unit, so it
// cannot see these overlaps. After the map is fitted, Cosmos also squeezes the
// cloud into a fixed box and then zooms, which draws each circle larger than
// its raw size. Reserve that on-screen radius, including the 64px cap.
function spreadCircles(flat: Float32Array, sizes: Float32Array): void {
  const count = sizes.length;
  if (count < 2) return;
  const canvas = stage.querySelector("canvas");
  const width = canvas?.clientWidth || stage.clientWidth || 900;
  const height = canvas?.clientHeight || stage.clientHeight || 700;
  const content = Math.max(120, Math.min(width, height) * 0.6);
  const zoom = content / (SPACE_SIZE * 0.1);
  const spanOf = (): number => {
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (let index = 0; index < count; index += 1) {
      const x = flat[index * 2] ?? 0;
      const y = flat[index * 2 + 1] ?? 0;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    return Math.max(maxX - minX, maxY - minY, 1);
  };
  for (let pass = 0; pass < 40; pass += 1) {
    const span = spanOf();
    const radii = new Float32Array(count);
    let maxRadius = 1;
    for (let index = 0; index < count; index += 1) {
      const drawn = Math.min((sizes[index] ?? 12) * zoom, 64);
      const radius = (drawn / 2 + 4) * (span / content);
      radii[index] = radius;
      if (radius > maxRadius) maxRadius = radius;
    }
    const cell = maxRadius * 2;
    const grid = new Map<string, number[]>();
    for (let index = 0; index < count; index += 1) {
      const bucket = `${Math.floor((flat[index * 2] ?? 0) / cell)}:${Math.floor((flat[index * 2 + 1] ?? 0) / cell)}`;
      const list = grid.get(bucket);
      if (list) list.push(index);
      else grid.set(bucket, [index]);
    }
    let moved = false;
    for (let index = 0; index < count; index += 1) {
      const cx = Math.floor((flat[index * 2] ?? 0) / cell);
      const cy = Math.floor((flat[index * 2 + 1] ?? 0) / cell);
      for (let ox = -1; ox <= 1; ox += 1) {
        for (let oy = -1; oy <= 1; oy += 1) {
          const list = grid.get(`${cx + ox}:${cy + oy}`);
          if (!list) continue;
          for (const other of list) {
            if (other <= index) continue;
            let dx = (flat[other * 2] ?? 0) - (flat[index * 2] ?? 0);
            let dy = (flat[other * 2 + 1] ?? 0) - (flat[index * 2 + 1] ?? 0);
            let dist = Math.hypot(dx, dy);
            const min = (radii[index] ?? 0) + (radii[other] ?? 0);
            if (dist >= min) continue;
            if (dist < 1e-4) {
              const angle = (index + 1) * 2.399963;
              dx = Math.cos(angle);
              dy = Math.sin(angle);
              dist = 1;
            }
            const push = (min - dist) / 2;
            const ux = (dx / dist) * push;
            const uy = (dy / dist) * push;
            flat[index * 2] = (flat[index * 2] ?? 0) - ux;
            flat[index * 2 + 1] = (flat[index * 2 + 1] ?? 0) - uy;
            flat[other * 2] = (flat[other * 2] ?? 0) + ux;
            flat[other * 2 + 1] = (flat[other * 2 + 1] ?? 0) + uy;
            moved = true;
          }
        }
      }
    }
    if (!moved) break;
  }
}

function worldRadii(flat: Float32Array, sizes: Float32Array): Float32Array {
  const count = sizes.length;
  const radii = new Float32Array(count);
  const canvas = stage.querySelector("canvas");
  const width = canvas?.clientWidth || stage.clientWidth || 900;
  const height = canvas?.clientHeight || stage.clientHeight || 700;
  const content = Math.max(120, Math.min(width, height) * 0.6);
  const zoom = content / (SPACE_SIZE * 0.1);
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (let index = 0; index < count; index += 1) {
    const x = flat[index * 2] ?? 0;
    const y = flat[index * 2 + 1] ?? 0;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  const span = Math.max(maxX - minX, maxY - minY, 1);
  const unit = span / content;
  for (let index = 0; index < count; index += 1) {
    const drawn = Math.min((sizes[index] ?? 12) * zoom, 64);
    radii[index] = (drawn / 2 + 10) * unit;
  }
  return radii;
}

function segmentsCross(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
  dx: number,
  dy: number,
): boolean {
  const side = (px: number, py: number, qx: number, qy: number, rx: number, ry: number) =>
    (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
  return side(ax, ay, bx, by, cx, cy) * side(ax, ay, bx, by, dx, dy) < 0
    && side(cx, cy, dx, dy, ax, ay) * side(cx, cy, dx, dy, bx, by) < 0;
}

// The opened look is a path. Notes you clicked sit on a loose arc.
// Each of their other links fans out on the open side, clear of the path.
function arrangeLook(flat: Float32Array, ids: string[], pairs: Array<[number, number]>, sizes: Float32Array): void {
  const at = new Map(ids.map((id, index) => [id, index]));
  const spine = trail.flatMap((id) => {
    const index = at.get(id);
    return index === undefined ? [] : [index];
  });
  if (spine.length === 0) return;
  const radius = (index: number) => (sizes[index] ?? CIRCLE_MIN) * 0.5;
  const air = 42;
  const along = [0];
  for (let step = 1; step < spine.length; step += 1) {
    const previous = spine[step - 1] ?? 0;
    const here = spine[step] ?? 0;
    along.push((along[step - 1] ?? 0) + radius(previous) + radius(here) + air);
  }
  const center = (along[along.length - 1] ?? 0) / 2;
  const bow = Math.max(48, (along[along.length - 1] ?? 0) * 0.2);
  spine.forEach((index, step) => {
    const x = (along[step] ?? 0) - center;
    const t = spine.length <= 1 ? 0.5 : step / (spine.length - 1);
    flat[index * 2] = x;
    flat[index * 2 + 1] = Math.sin(t * Math.PI) * bow;
  });
  const onSpine = new Set(spine);
  const sprouts = new Map<number, number[]>();
  for (const [left, right] of pairs) {
    const parent = onSpine.has(left) ? left : onSpine.has(right) ? right : -1;
    const child = parent === left ? right : parent === right ? left : -1;
    if (parent < 0 || child < 0 || onSpine.has(child)) continue;
    const list = sprouts.get(parent) ?? [];
    if (!list.includes(child)) list.push(child);
    sprouts.set(parent, list);
  }
  spine.forEach((index, step) => {
    const children = sprouts.get(index) ?? [];
    if (children.length === 0) return;
    const previous = spine[step - 1];
    const next = spine[step + 1];
    const px = flat[index * 2] ?? 0;
    const py = flat[index * 2 + 1] ?? 0;
    let tx = 1;
    let ty = 0;
    if (previous !== undefined && next !== undefined) {
      tx = (flat[next * 2] ?? 0) - (flat[previous * 2] ?? 0);
      ty = (flat[next * 2 + 1] ?? 0) - (flat[previous * 2 + 1] ?? 0);
    } else if (next !== undefined) {
      tx = (flat[next * 2] ?? 0) - px;
      ty = (flat[next * 2 + 1] ?? 0) - py;
    } else if (previous !== undefined) {
      tx = px - (flat[previous * 2] ?? 0);
      ty = py - (flat[previous * 2 + 1] ?? 0);
    }
    const span = Math.hypot(tx, ty) || 1;
    const flip = step % 2 === 0 ? 1 : -1;
    const base = Math.atan2((tx / span) * flip, (-ty / span) * flip);
    children.forEach((child, childIndex) => {
      const spread = children.length === 1 ? 0 : (childIndex - (children.length - 1) / 2) * 0.72;
      const angle = base + spread;
      const dist = radius(index) + radius(child) + air;
      flat[child * 2] = px + Math.cos(angle) * dist;
      flat[child * 2 + 1] = py + Math.sin(angle) * dist;
    });
  });
}

// Each view moves a note off a link it does not belong to, and eases crossed links apart.
function clearCrossings(
  flat: Float32Array,
  pairs: Array<[number, number]>,
  sizes: Float32Array,
  rounds: number,
  pinned: Set<number>,
  firm: boolean,
): void {
  const count = flat.length / 2;
  if (count < 2 || pairs.length < 1) return;
  for (let round = 0; round < rounds; round += 1) {
    const radii = worldRadii(flat, sizes);
    for (const [left, right] of pairs) {
      const ax = flat[left * 2] ?? 0;
      const ay = flat[left * 2 + 1] ?? 0;
      const bx = flat[right * 2] ?? 0;
      const by = flat[right * 2 + 1] ?? 0;
      const abx = bx - ax;
      const aby = by - ay;
      const length2 = abx * abx + aby * aby || 1;
      for (let index = 0; index < count; index += 1) {
        if (index === left || index === right) continue;
        const px = flat[index * 2] ?? 0;
        const py = flat[index * 2 + 1] ?? 0;
        const along = Math.max(0, Math.min(1, ((px - ax) * abx + (py - ay) * aby) / length2));
        if (along < 0.12 || along > 0.88) continue;
        const qx = ax + abx * along;
        const qy = ay + aby * along;
        let dx = px - qx;
        let dy = py - qy;
        let dist = Math.hypot(dx, dy);
        const need = radii[index] ?? 0;
        if (dist >= need) continue;
        if (dist < 1e-3) {
          dx = -aby;
          dy = abx;
          dist = Math.hypot(dx, dy) || 1;
        }
        const push = (need - dist) * (firm ? 1 : 0.72);
        if (pinned.has(index)) {
          const free = pinned.has(left) ? (pinned.has(right) ? -1 : right) : left;
          if (free < 0) continue;
          flat[free * 2] = (flat[free * 2] ?? 0) - (dx / dist) * push;
          flat[free * 2 + 1] = (flat[free * 2 + 1] ?? 0) - (dy / dist) * push;
        } else {
          flat[index * 2] = px + (dx / dist) * push;
          flat[index * 2 + 1] = py + (dy / dist) * push;
        }
      }
    }
    for (let first = 0; first < pairs.length; first += 1) {
      for (let second = first + 1; second < pairs.length; second += 1) {
        const [a, b] = pairs[first] ?? [0, 0];
        const [c, d] = pairs[second] ?? [0, 0];
        if (a === c || a === d || b === c || b === d) continue;
        const ax = flat[a * 2] ?? 0;
        const ay = flat[a * 2 + 1] ?? 0;
        const bx = flat[b * 2] ?? 0;
        const by = flat[b * 2 + 1] ?? 0;
        const cx = flat[c * 2] ?? 0;
        const cy = flat[c * 2 + 1] ?? 0;
        const dx = flat[d * 2] ?? 0;
        const dy = flat[d * 2 + 1] ?? 0;
        if (!segmentsCross(ax, ay, bx, by, cx, cy, dx, dy)) continue;
        const abx = bx - ax;
        const aby = by - ay;
        const span = Math.hypot(abx, aby) || 1;
        const step = firm
          ? Math.max(18, ((radii[a] ?? 0) + (radii[c] ?? 0)) * 0.35)
          : ((radii[a] ?? 0) + (radii[c] ?? 0)) * 0.08;
        const px = (-aby / span) * step;
        const py = (abx / span) * step;
        const nudge = (index: number, sign: number) => {
          if (pinned.has(index)) return;
          flat[index * 2] = (flat[index * 2] ?? 0) + px * sign;
          flat[index * 2 + 1] = (flat[index * 2 + 1] ?? 0) + py * sign;
        };
        nudge(a, -1);
        nudge(b, -1);
        nudge(c, 1);
        nudge(d, 1);
      }
    }
  }
}

// A short relaxation on the notes in this view. Linked notes drift toward a
// comfortable gap and the rest stay apart, without washing out the loose start.
function settle(flat: Float32Array, pairs: Array<[number, number]>, ideal: number, passes: number, pull: number): void {
  const count = flat.length / 2;
  const gap = ideal * 0.82;
  for (let pass = 0; pass < passes; pass += 1) {
    for (const [left, right] of pairs) {
      let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
      let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
      let dist = Math.hypot(dx, dy);
      if (dist < 1e-3) {
        const angle = (left + 1) * 2.399963;
        dx = Math.cos(angle);
        dy = Math.sin(angle);
        dist = 1;
      }
      const shift = (dist - ideal) * pull * 0.5;
      const ux = (dx / dist) * shift;
      const uy = (dy / dist) * shift;
      flat[left * 2] = (flat[left * 2] ?? 0) + ux;
      flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) + uy;
      flat[right * 2] = (flat[right * 2] ?? 0) - ux;
      flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) - uy;
    }
    for (let left = 0; left < count; left += 1) {
      for (let right = left + 1; right < count; right += 1) {
        let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
        let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
        let dist = Math.hypot(dx, dy);
        if (dist >= gap) continue;
        if (dist < 1e-3) {
          const angle = (left + 1) * 2.399963;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          dist = 1;
        }
        const push = (gap - dist) * 0.06;
        const ux = (dx / dist) * push;
        const uy = (dy / dist) * push;
        flat[left * 2] = (flat[left * 2] ?? 0) - ux;
        flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) - uy;
        flat[right * 2] = (flat[right * 2] ?? 0) + ux;
        flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) + uy;
      }
    }
  }
}

async function mount(): Promise<void> {
  graph?.destroy();
  stage.innerHTML = "";
  const created = new Graph(stage, {
    backgroundColor: "#14181f",
    spaceSize: SPACE_SIZE,
    enableSimulation: false,
    pointDefaultSize: 14,
    linkDefaultWidth: 1.4,
    scalePointsOnZoom: true,
    simulationLinkDistance: 40,
    simulationRepulsion: 1.2,
    curvedLinks: true,
    curvedLinkWeight: 0.42,
    curvedLinkControlPointDistance: 0.07,
    linkDashLength: 11,
    linkDashGap: 8,
    renderHoveredPointRing: true,
    hoveredPointRingColor: "#f4f0e6",
    focusedPointRingColor: "#ffe08a",
    hoveredPointCursor: "pointer",
    onZoom: () => placeDegreeLabels(),
    onZoomEnd: () => placeDegreeLabels(),
    fitViewOnInit: true,
    fitViewDelay: 300,
    onPointClick: (index) => {
      const id = drawnIds[index];
      if (!id || !openNote(id)) return;
      paint(true);
    },
  });
  graph = created;
  await created.ready;
  paint(true);
}

function noteTitle(id: string): string {
  const text = lab.vault.get(id)?.text ?? "";
  const line = text.split("\n")[0]?.trim() ?? "";
  if (!line) return "Note";
  return line.length > 72 ? `${line.slice(0, 69)}…` : line;
}

function renderOpenedNotes(): void {
  for (const id of openBlocks) {
    if (!trail.includes(id)) openBlocks.delete(id);
  }
  noteFacts.replaceChildren();
  if (trail.length === 0) {
    source.hidden = false;
    source.textContent = "Click a note on the map.";
    return;
  }
  source.hidden = true;
  for (const id of trail) {
    const event = lab.vault.get(id);
    const pointer = lab.pointer(id);
    const degree = lab.view(personId).nodes.find((node) => node.id === id)?.degree ?? 0;
    const rows = [
      ["Kind", sourceName(event?.sourceType ?? "hub")],
      ["Date", event?.capturedAt.slice(0, 10) || "—"],
      ["Links", String(degree)],
      ["Came in", event ? arrivalName(event.sourceArrival) : "—"],
      ["Independence", event ? independenceName(event.independence) : "—"],
    ];
    const block = document.createElement("details");
    block.className = "opened-note";
    const summary = document.createElement("summary");
    summary.textContent = noteTitle(id);
    block.append(summary);
    for (const [label, value] of rows) {
      const row = document.createElement("div");
      row.className = "fact";
      const term = document.createElement("dt");
      const detail = document.createElement("dd");
      term.textContent = label;
      detail.textContent = value;
      row.append(term, detail);
      block.append(row);
    }
    const body = document.createElement("p");
    body.className = "note-text";
    if (event) body.textContent = event.text;
    else if (pointer) body.textContent = `Record with ${pointer.memberEventIds.length} source notes.`;
    else body.textContent = "No text stored for this note.";
    block.append(body);
    block.addEventListener("toggle", () => {
      if (block.open) openBlocks.add(id);
      else openBlocks.delete(id);
    });
    block.open = openBlocks.has(id);
    noteFacts.append(block);
  }
}

function openNote(id: string): boolean {
  if (showAll) trail = [id];
  else {
    const at = trail.indexOf(id);
    if (at >= 0) trail = trail.slice(0, at + 1);
    else {
      const latest = trail[trail.length - 1];
      const linkedToLatest = latest !== undefined && (neighborMap().get(latest) ?? []).includes(id);
      if (!linkedToLatest) return false;
      trail = [...trail, id];
    }
  }
  showAll = false;
  selectedId = id;
  openBlocks.add(id);
  renderOpenedNotes();
  return true;
}

function renderAssessments(): void {
  const rows = lab.localAssessments(personId);
  assessments.innerHTML =
    rows.length === 0
      ? "<li>None yet. Save a note below to see what may relate.</li>"
      : rows
          .map((row) => {
            const said = row.judgment === "no_link" ? "does not appear related" : "not sure yet";
            const edge = row.activeEdge ? "recorded link stays" : "no recorded link";
            return `<li>${escapeHtml(`${said} · ${RELATION_LABEL[row.relation]} · ${edge} · ${row.excerpt} / ${row.otherExcerpt}`)}</li>`;
          })
          .join("");
}

function shownIds(neighbors: Map<string, string[]>): Set<string> {
  const keep = new Set(trail);
  for (const id of trail) {
    for (const next of neighbors.get(id) ?? []) keep.add(next);
  }
  return keep;
}

function trailSteps(): Array<[string, string]> {
  const neighbors = neighborMap();
  const steps: Array<[string, string]> = [];
  for (let step = 1; step < trail.length; step += 1) {
    const toward = trail[step];
    if (!toward) continue;
    for (let earlier = step - 1; earlier >= 0; earlier -= 1) {
      const candidate = trail[earlier];
      if (candidate && (neighbors.get(candidate) ?? []).includes(toward)) {
        steps.push([candidate, toward]);
        break;
      }
    }
  }
  return steps;
}

function linkColor(sourceId: string, targetId: string, clicked: Set<string>): [number, number, number, number] {
  if (showAll) return MAP_LINK;
  if (clicked.has(sourceId) || clicked.has(targetId)) return CONNECTOR_LINK;
  return FAINT_LINK;
}

function paint(fit: boolean): void {
  if (!graph) return;
  const view = lab.view(personId);
  if (positions.length / 2 !== view.nodes.length) positions = layout(view);
  const neighbors = neighborMap();
  const clicked = new Set(trail);
  const keep = showAll ? null : shownIds(neighbors);
  const indexes: number[] = [];
  view.nodes.forEach((node, index) => {
    if (showAll || keep?.has(node.id)) indexes.push(index);
  });
  drawnIds = indexes.map((index) => view.nodes[index]?.id ?? "");
  const pointPositions = new Float32Array(drawnIds.length * 2);
  const colors = new Float32Array(drawnIds.length * 4);
  const degrees = indexes.map((fullIndex) => neighbors.get(view.nodes[fullIndex]?.id ?? "")?.length ?? 0);
  const sizes = circleSizes(degrees);
  labelState = [];
  indexes.forEach((fullIndex, index) => {
    const id = view.nodes[fullIndex]?.id ?? "";
    const x = positions[fullIndex * 2] ?? 0;
    const y = positions[fullIndex * 2 + 1] ?? 0;
    pointPositions[index * 2] = x;
    pointPositions[index * 2 + 1] = y;
    const kind = view.nodes[fullIndex]?.sourceType ?? "hub";
    const latest = trail[trail.length - 1];
    const nextToLatest = latest !== undefined && (neighbors.get(latest) ?? []).includes(id);
    const rgb = KIND_RGB[kind] ?? KIND_RGB.hub ?? [0.62, 0.66, 0.7];
    const alpha = showAll || clicked.has(id) || nextToLatest ? 1 : 0.38;
    colors.set([rgb[0], rgb[1], rgb[2], alpha], index * 4);
    const degree = degrees[index] ?? 0;
    const size = sizes[index] ?? CIRCLE_MIN;
    labelState.push({ id, x, y, degree, size });
  });
  const drawnIndex = new Map(drawnIds.map((id, index) => [id, index]));
  const kept = view.links.filter((link) => {
    const sourceId = view.nodes[link.source]?.id;
    const targetId = view.nodes[link.target]?.id;
    return sourceId !== undefined && targetId !== undefined && drawnIndex.has(sourceId) && drawnIndex.has(targetId);
  });
  const pairs = kept.flatMap((link) => {
    const sourceId = view.nodes[link.source]?.id;
    const targetId = view.nodes[link.target]?.id;
    if (!sourceId || !targetId) return [];
    const left = drawnIndex.get(sourceId);
    const right = drawnIndex.get(targetId);
    return left === undefined || right === undefined ? [] : [[left, right] as [number, number]];
  });
  const pinned = new Set<number>();
  if (showAll) {
    settle(pointPositions, pairs, 96, 14, 0.045);
  } else {
    drawnIds.forEach((id, index) => {
      if (trail.includes(id)) pinned.add(index);
    });
    arrangeLook(pointPositions, drawnIds, pairs, sizes);
  }
  const stepDirection = new Map<string, [string, string]>();
  for (const [from, toward] of trailSteps()) {
    const key = from < toward ? `${from}|${toward}` : `${toward}|${from}`;
    stepDirection.set(key, [from, toward]);
  }
  const links = new Float32Array(kept.length * 2);
  const linkColors = new Float32Array(kept.length * 4);
  const linkWidths = new Float32Array(kept.length);
  const linkStyles = new Float32Array(kept.length);
  kept.forEach((link, index) => {
    const sourceId = view.nodes[link.source]?.id ?? "";
    const targetId = view.nodes[link.target]?.id ?? "";
    const key = sourceId < targetId ? `${sourceId}|${targetId}` : `${targetId}|${sourceId}`;
    const directed = stepDirection.get(key);
    const fromId = directed?.[0] ?? sourceId;
    const toId = directed?.[1] ?? targetId;
    links[index * 2] = drawnIndex.get(fromId) ?? 0;
    links[index * 2 + 1] = drawnIndex.get(toId) ?? 0;
    const onStep = directed !== undefined;
    linkColors.set(onStep ? [0, 0, 0, 0] : linkColor(sourceId, targetId, clicked), index * 4);
    const touched = clicked.has(sourceId) || clicked.has(targetId);
    linkWidths[index] = showAll ? 1.15 : onStep ? 0 : touched ? 1.35 : 0.85;
    linkStyles[index] = 0;
  });
  if (showAll) {
    spreadCircles(pointPositions, sizes);
    clearCrossings(pointPositions, pairs, sizes, 8, pinned, false);
    spreadCircles(pointPositions, sizes);
  } else {
    clearCrossings(pointPositions, pairs, sizes, 12, pinned, true);
  }
  labelState.forEach((item, index) => {
    item.x = pointPositions[index * 2] ?? item.x;
    item.y = pointPositions[index * 2 + 1] ?? item.y;
  });
  graph.setPointPositions(pointPositions);
  graph.setPointColors(colors);
  graph.setPointSizes(sizes);
  graph.setLinks(links);
  graph.setLinkColors(linkColors);
  graph.setLinkWidths(linkWidths);
  graph.setLinkStyles(linkStyles);
  graph.render(undefined, 0);
  focusOpenedNote();
  if (fit && pointPositions.length > 0) fitPicture(pointPositions);
  else placeDegreeLabels();
}

function focusOpenedNote(): void {
  if (!graph) return;
  const index = !showAll && selectedId ? drawnIds.indexOf(selectedId) : -1;
  graph.setConfigPartial({ focusedPointIndex: index >= 0 ? index : undefined });
}

function fitPicture(pointPositions: Float32Array): void {
  const positions = Array.from(pointPositions);
  const apply = (): void => {
    if (!graph) return;
    graph.pause();
    graph.fitViewByPointPositions(positions, 0, 0.2, false);
  };
  apply();
  requestAnimationFrame(() => {
    apply();
    requestAnimationFrame(() => placeDegreeLabels());
  });
}

capture.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = noteInput.value.trim();
  if (!text) return;
  storeButton.disabled = true;
  suggestStatus.textContent = "Looking for context that may relate.";
  void lab
    .ingest({
      personId: personId,
      text,
      sourceType: "note",
      capturedAt: new Date().toISOString(),
      lineageId: `manual-${text.slice(0, 24)}`,
      independence: "unknown",
      sourceArrival: "typed",
      idempotencyKey: `manual-${Date.now()}`,
    })
    .then((result) => {
      const counts = { link: 0, no_link: 0, uncertain: 0 };
      for (const judgment of result.judgments) {
        if (judgment.accepted) counts[judgment.judgment] += 1;
      }
      trail = [result.eventId];
      selectedId = result.eventId;
      showAll = false;
      renderOpenedNotes();
      suggestStatus.textContent = `Saved. ${counts.link} may relate, ${counts.no_link} do not appear related, ${counts.uncertain} not sure yet. A “does not appear related” stays in this list and does not erase a recorded link.`;
      paint(true);
    })
    .finally(() => {
      storeButton.disabled = false;
    });
});

function clearChoice(): void {
  trail = [];
  openBlocks.clear();
  selectedId = null;
  showAll = true;
  renderOpenedNotes();
  document.querySelector("aside")?.scrollTo(0, 0);
  paint(true);
}

function conicPoint(
  start: { x: number; y: number },
  end: { x: number; y: number },
  control: { x: number; y: number },
  t: number,
): { x: number; y: number } {
  const remain = 1 - t;
  const weight = 0.42;
  const x = remain * remain * start.x + 2 * remain * t * weight * control.x + t * t * end.x;
  const y = remain * remain * start.y + 2 * remain * t * weight * control.y + t * t * end.y;
  const divisor = remain * remain + 2 * remain * t * weight + t * t;
  return { x: x / divisor, y: y / divisor };
}

function placeMovingPipes(
  space: Map<string, { x: number; y: number }>,
  screen: Map<string, { x: number; y: number; radius: number }>,
  offsetX: number,
  offsetY: number,
): void {
  if (!graph || showAll) return;
  const steps = trailSteps();
  if (steps.length === 0) return;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "pipe-flow");
  for (const [from, toward] of steps) {
    const start = space.get(from);
    const end = space.get(toward);
    const startScreen = screen.get(from);
    const endScreen = screen.get(toward);
    if (!start || !end || !startScreen || !endScreen) continue;
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const length = Math.hypot(dx, dy) || 1;
    const control = {
      x: (start.x + end.x) / 2 + (-dy / length) * length * 0.07,
      y: (start.y + end.y) / 2 + (dx / length) * length * 0.07,
    };
    const samples: Array<{ x: number; y: number; open: boolean }> = [];
    for (let index = 0; index <= 32; index += 1) {
      const point = conicPoint(start, end, control, index / 32);
      const [sx, sy] = graph.spaceToScreenPosition([point.x, point.y]);
      const x = offsetX + sx;
      const y = offsetY + sy;
      const blocked = [...screen.values()].some(
        (spot) => Math.hypot(x - spot.x, y - spot.y) < spot.radius + 7,
      );
      samples.push({ x, y, open: !blocked });
    }
    let run: Array<{ x: number; y: number }> = [];
    const flush = (): void => {
      if (run.length < 2) {
        run = [];
        return;
      }
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "dash");
      path.setAttribute(
        "d",
        run.map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`).join(" "),
      );
      svg.append(path);
      run = [];
    };
    for (const sample of samples) {
      if (sample.open) run.push(sample);
      else flush();
    }
    flush();
  }
  if (svg.querySelector("path")) degreeLabels.append(svg);
}

function placeDegreeLabels(): void {
  degreeLabels.replaceChildren();
  if (!graph || labelState.length === 0) return;
  const canvas = stage.querySelector("canvas");
  if (!canvas) return;
  const canvasBox = canvas.getBoundingClientRect();
  const layerBox = degreeLabels.getBoundingClientRect();
  const offsetX = canvasBox.left - layerBox.left;
  const offsetY = canvasBox.top - layerBox.top;
  const flat = new Float32Array(labelState.length * 2);
  labelState.forEach((item, index) => {
    flat[index * 2] = item.x;
    flat[index * 2 + 1] = item.y;
  });
  const rescale = rescaleToSpace(flat);
  const screen = new Map<string, { x: number; y: number; radius: number }>();
  const space = new Map<string, { x: number; y: number }>();
  for (const item of labelState) {
    const diameter = Math.min(item.size * graph.getZoomLevel(), 64);
    const x = rescale.x(item.x);
    const y = rescale.y(item.y);
    const [sx, sy] = graph.spaceToScreenPosition([x, y]);
    screen.set(item.id, { x: offsetX + sx, y: offsetY + sy, radius: diameter / 2 });
    space.set(item.id, { x, y });
  }
  placeMovingPipes(space, screen, offsetX, offsetY);
  const origin = trail[0];
  const earlier = new Set(trail.slice(0, -1));
  for (const item of labelState) {
    const isOrigin = item.id === origin;
    if (!isOrigin && !earlier.has(item.id)) continue;
    const spot = screen.get(item.id);
    if (!spot) continue;
    if (spot.x < -20 || spot.y < -20 || spot.x > canvas.clientWidth + 20 || spot.y > canvas.clientHeight + 20) continue;
    const ring = document.createElement("i");
    ring.className = isOrigin ? "trail-ring is-start" : "trail-ring";
    const box = spot.radius * 2 + (isOrigin ? 16 : 10);
    ring.style.left = `${spot.x}px`;
    ring.style.top = `${spot.y}px`;
    ring.style.width = `${box}px`;
    ring.style.height = `${box}px`;
    degreeLabels.appendChild(ring);
  }
  const placed: Array<{ x: number; y: number; radius: number }> = [];
  const ordered = [...labelState].sort((left, right) => right.size - left.size);
  for (const item of ordered) {
    const digits = String(item.degree).length;
    const diameter = Math.min(item.size * graph.getZoomLevel(), 64);
    if (diameter < (digits > 1 ? 34 : 24)) continue;
    const [sx, sy] = graph.spaceToScreenPosition([rescale.x(item.x), rescale.y(item.y)]);
    if (sx < -20 || sy < -20 || sx > canvas.clientWidth + 20 || sy > canvas.clientHeight + 20) continue;
    const radius = diameter / 2;
    const crowded = placed.some((other) => Math.hypot(other.x - sx, other.y - sy) < (other.radius + radius) * 0.82);
    if (crowded) continue;
    placed.push({ x: sx, y: sy, radius });
    const span = document.createElement("span");
    span.textContent = String(item.degree);
    span.style.left = `${offsetX + sx}px`;
    span.style.top = `${offsetY + sy}px`;
    span.style.fontSize = `${Math.min(15, diameter * 0.34)}px`;
    degreeLabels.appendChild(span);
  }
}

function rescaleToSpace(flat: Float32Array): { x: (value: number) => number; y: (value: number) => number } {
  const count = flat.length / 2;
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (let index = 0; index < count; index += 1) {
    const x = flat[index * 2] ?? 0;
    const y = flat[index * 2 + 1] ?? 0;
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const span = Math.max(spanX, spanY);
  if (span > SPACE_SIZE) return { x: (value) => value, y: (value) => value };
  if (!Number.isFinite(minX) || span === 0) {
    const mid = SPACE_SIZE / 2;
    return { x: (value) => value - minX + mid, y: (value) => value - minY + mid };
  }
  const crowded = count > SPACE_SIZE * SPACE_SIZE * 1e-3;
  const box = crowded ? SPACE_SIZE * Math.max(1.2, Math.sqrt(count) / SPACE_SIZE) : SPACE_SIZE * 0.1;
  const scale = box / span;
  const pad = (SPACE_SIZE - box) / 2;
  const originX = ((span - spanX) / 2) * scale + pad;
  const originY = ((span - spanY) / 2) * scale + pad;
  return {
    x: (value) => (value - minX) * scale + originX,
    y: (value) => (value - minY) * scale + originY,
  };
}

function neighborMap(): Map<string, string[]> {
  const view = lab.view(personId);
  const neighbors = new Map<string, string[]>();
  for (const node of view.nodes) neighbors.set(node.id, []);
  for (const link of view.links) {
    const sourceId = view.nodes[link.source]?.id;
    const targetId = view.nodes[link.target]?.id;
    if (!sourceId || !targetId || sourceId === targetId) continue;
    neighbors.get(sourceId)?.push(targetId);
    neighbors.get(targetId)?.push(sourceId);
  }
  return neighbors;
}

resetButton.addEventListener("click", () => clearChoice());

function markPeople(): void {
  for (const button of peopleNav.querySelectorAll("button")) {
    button.classList.toggle("is-current", button.dataset.person === personId);
  }
}

function useLab(next: RawContextLab, id: string): void {
  personId = id;
  lab = next;
  positions = layout(lab.view(personId));
  trail = [];
  openBlocks.clear();
  selectedId = null;
  showAll = true;
  renderOpenedNotes();
  notePop.hidden = true;
  noteAdd.hidden = false;
  markPeople();
  renderAssessments();
  void mount().catch((error: unknown) => {
    source.textContent = error instanceof Error ? error.message : "The map view failed to start.";
  });
}

newNoteButton.addEventListener("click", () => {
  notePop.hidden = !notePop.hidden;
});

void loadCasePeople()
  .then((people) => {
    for (const file of people) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = file.label;
      button.dataset.person = file.personId;
      button.addEventListener("click", () => useLab(labFromCase(file), file.personId));
      peopleNav.append(button);
    }
    const first = people[0];
    if (first) useLab(labFromCase(first), first.personId);
    else {
      noteAdd.hidden = true;
      source.textContent = "No person is loaded.";
      renderAssessments();
      return mount();
    }
    return undefined;
  })
  .catch((error: unknown) => {
    noteAdd.hidden = true;
    source.textContent = error instanceof Error ? error.message : "The research cases could not be loaded.";
  });
