import { Graph } from "@cosmos.gl/graph";
import { loadCasePeople, labFromCase } from "../cases.js";
import { LEGEND_KINDS, RECORD_KINDS, RELATION_LABEL, arrivalName, independenceName, sourceName } from "../relation.js";
import { RawContextLab } from "../router.js";
import { memoryKeyword } from "./keyword.js";
import { growLook, HOP_DIAMETERS, type Point } from "./look-layout.js";
import { mapSettings } from "./settings.js";
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

function paintRecordKey(): void {
  const key = document.querySelector("#record-key");
  if (!key) return;
  key.replaceChildren(
    ...LEGEND_KINDS.map((id) => {
      const kind = RECORD_KINDS[id];
      const row = document.createElement("span");
      const swatch = document.createElement("i");
      swatch.className = "swatch";
      swatch.style.background = kind.hex;
      row.append(swatch, document.createTextNode(kind.label));
      return row;
    }),
  );
}

paintRecordKey();
source.textContent = mapSettings.copy.emptyMap;

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
const CONNECTOR_LINK: [number, number, number, number] = [0.2, 0.25, 0.33, 0.72];
const FAINT_LINK: [number, number, number, number] = [0.39, 0.45, 0.55, 0.38];
const MAP_LINK: [number, number, number, number] = [0.39, 0.45, 0.55, 0.55];
const KIND_RGB: Record<string, readonly [number, number, number]> = Object.fromEntries(
  Object.entries(RECORD_KINDS).map(([id, kind]) => [id, kind.rgb]),
);

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
/** Last coordinates painted on the full map, keyed by note id. */
const mapPositions = new Map<string, Point>();
/** Coordinates of the opened look. Notes already here stay put. */
const lookPositions = new Map<string, Point>();
/** Space scale from the first frame of this look. Later clicks reuse it. */
let frozenScale: { x: (value: number) => number; y: (value: number) => number } | null = null;
let fitToken = 0;
let driftToken = 0;

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
      : rank * mapSettings.turn + wobble * 0.55;
    pos[item.index * 2] = Math.cos(angle) * radius;
    pos[item.index * 2 + 1] = Math.sin(angle) * radius;
  });
  return pos;
}

const STAGE_BG: [number, number, number] = [20 / 255, 24 / 255, 31 / 255];

// One link count is one size, on the full map and on every step of a path.
// A count of 3 is a little larger than 2. The view does not restretch them.
function circleSize(degree: number): number {
  return mapSettings.circle.base + degree * mapSettings.circle.perLink;
}

function circleSizes(degrees: ArrayLike<number>): Float32Array {
  const sizes = new Float32Array(degrees.length);
  for (let index = 0; index < degrees.length; index += 1) sizes[index] = circleSize(degrees[index] ?? 0);
  return sizes;
}

function paintColor(rgb: readonly [number, number, number], alpha: number): [number, number, number, number] {
  return [
    rgb[0] * alpha + STAGE_BG[0] * (1 - alpha),
    rgb[1] * alpha + STAGE_BG[1] * (1 - alpha),
    rgb[2] * alpha + STAGE_BG[2] * (1 - alpha),
    1,
  ];
}

// Pixel size of a circle, turned back into layout units after the cloud is fitted.
function reservedRadii(flat: Float32Array, sizes: Float32Array, pad: number): Float32Array {
  const count = sizes.length;
  const radii = new Float32Array(count);
  const canvas = stage.querySelector("canvas");
  const clearance = mapSettings.clearance;
  const width = canvas?.clientWidth || stage.clientWidth || clearance.fallbackWidth;
  const height = canvas?.clientHeight || stage.clientHeight || clearance.fallbackHeight;
  const content = Math.max(clearance.minContent, Math.min(width, height) * clearance.contentFraction);
  const zoom = content / (SPACE_SIZE * clearance.fittedFraction);
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
    const drawn = Math.min((sizes[index] ?? clearance.fallbackSize) * zoom, clearance.pointCap);
    radii[index] = (drawn / 2 + pad) * unit;
  }
  return radii;
}

// Cosmos simulationCollision treats a circle's pixel size as a map unit, so it
// cannot see these overlaps. After the map is fitted, Cosmos also squeezes the
// cloud into a fixed box and then zooms, which draws each circle larger than
// its raw size. Reserve that on-screen radius, including the 64px cap.
function spreadCircles(flat: Float32Array, sizes: Float32Array): void {
  const count = sizes.length;
  if (count < 2) return;
  const radii = reservedRadii(flat, sizes, mapSettings.clearance.spreadPad);
  let maxRadius = 1;
  for (let index = 0; index < count; index += 1) {
    if ((radii[index] ?? 0) > maxRadius) maxRadius = radii[index] ?? 1;
  }
  for (let pass = 0; pass < 40; pass += 1) {
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
              const angle = (index + 1) * mapSettings.turn;
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
  return reservedRadii(flat, sizes, mapSettings.clearance.linkPad);
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

// The full map eases a note off a link it does not belong to, and eases crossed links apart.
function clearCrossings(flat: Float32Array, pairs: Array<[number, number]>, sizes: Float32Array, rounds: number): void {
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
        if (along < mapSettings.linkBand.start || along > mapSettings.linkBand.end) continue;
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
        const push = (need - dist) * 0.72;
        flat[index * 2] = px + (dx / dist) * push;
        flat[index * 2 + 1] = py + (dy / dist) * push;
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
        const step = ((radii[a] ?? 0) + (radii[c] ?? 0)) * 0.08;
        const px = (-aby / span) * step;
        const py = (abx / span) * step;
        flat[a * 2] = ax - px;
        flat[a * 2 + 1] = ay - py;
        flat[b * 2] = bx - px;
        flat[b * 2 + 1] = by - py;
        flat[c * 2] = cx + px;
        flat[c * 2 + 1] = cy + py;
        flat[d * 2] = dx + px;
        flat[d * 2 + 1] = dy + py;
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
        const angle = (left + 1) * mapSettings.turn;
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
          const angle = (left + 1) * mapSettings.turn;
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
    backgroundColor: "#ffffff",
    spaceSize: SPACE_SIZE,
    enableSimulation: false,
    rescalePositions: true,
    fitViewOnInit: false,
    simulationGravity: 0,
    simulationCenter: 0,
    simulationCluster: 0,
    simulationLinkSpring: 0,
    simulationRepulsion: 0,
    pointDefaultSize: 14,
    linkDefaultWidth: 1.4,
    scalePointsOnZoom: true,
    curvedLinks: true,
    curvedLinkWeight: mapSettings.curve.weight,
    curvedLinkControlPointDistance: mapSettings.curve.control,
    linkDashLength: 11,
    linkDashGap: 8,
    renderHoveredPointRing: true,
    hoveredPointRingColor: "#334155",
    focusedPointRingColor: "#ffe08a",
    hoveredPointCursor: "grab",
    enableDrag: true,
    onDrag: (event) => {
      const source = event.sourceEvent;
      if (source instanceof PointerEvent) placeFromPointer(source);
    },
    onDragEnd: () => finishDrag(),
    onZoom: () => placeDegreeLabels(),
    onZoomEnd: () => placeDegreeLabels(),
    onPointMouseOver: (index) => {
      const id = drawnIds[index];
      highlightOpened(id ?? null);
    },
    onPointMouseOut: () => highlightOpened(null),
    onPointClick: (index) => {
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      const id = drawnIds[index];
      if (id) openCircle(id);
    },
  });
  graph = created;
  await created.ready;
  paint(true);
}

function noteKeyword(event: { text: string; keyword?: string } | undefined): string {
  const stored = event?.keyword?.trim();
  if (stored) return stored;
  return memoryKeyword(event?.text ?? "");
}

const ASIDE_TITLE_LIMIT = mapSettings.headline.asideLimit;

/** Words a person can match against the keyword. Splits on punctuation, so HLA-B51 yields hla and b51. */
function asideTokens(value: string): string[] {
  return value.toLowerCase().split(/[^a-z0-9+]+/).filter((word) => word.length > 0);
}

/**
 * A short line under the keyword, only when it says something the keyword does not.
 * The note body already shows the full text, so a repeat of that first line stays out.
 */
function asideTitle(text: string, keyword: string): string {
  const line = text.split("\n")[0]?.trim() ?? "";
  if (!line) return "";
  const key = keyword.trim().toLowerCase();
  const keywordIsAWord = key.length > 0 && asideTokens(line).includes(key);
  const colon = line.indexOf(":");
  let extra = "";
  if (colon > 0 && colon <= mapSettings.headline.colonWindow) {
    const label = line.slice(0, colon).trim();
    const value = line.slice(colon + 1).trim();
    const labelTokens = asideTokens(label);
    const labelIsKeyword = key.length > 0 && labelTokens.length === 1 && labelTokens[0] === key;
    if (labelIsKeyword) extra = value;
    else if (!keywordIsAWord) extra = line;
    else if (value && value.length <= ASIDE_TITLE_LIMIT) extra = value;
  } else if (!keywordIsAWord) {
    extra = line;
  }
  if (!extra || (key.length > 0 && extra.toLowerCase() === key)) return "";
  return clipAside(extra);
}

function clipAside(value: string): string {
  if (value.length <= ASIDE_TITLE_LIMIT) return value;
  const room = value.slice(0, ASIDE_TITLE_LIMIT - 1);
  const space = room.lastIndexOf(" ");
  const trimmed = (space > mapSettings.headline.clipBreakAfter ? room.slice(0, space) : room).trimEnd();
  return `${trimmed}…`;
}

function renderOpenedNotes(): void {
  for (const id of openBlocks) {
    if (!trail.includes(id)) openBlocks.delete(id);
  }
  noteFacts.replaceChildren();
  if (trail.length === 0) {
    source.hidden = false;
    source.textContent = mapSettings.copy.emptyMap;
    return;
  }
  source.hidden = true;
  for (const id of trail) {
    const event = lab.vault.get(id);
    const pointer = lab.pointer(id);
    const degree = lab.view(personId).nodes.find((node) => node.id === id)?.degree ?? 0;
    const at = trail.indexOf(id);
    const previous = trail[at - 1];
    const step = previous ? lab.projection.edgeBetween(previous, id) : undefined;
    const recordRows: Array<[string, string]> = [
      ["Kind", sourceName(event?.sourceType ?? "hub")],
      ["Date", event?.capturedAt.slice(0, 10) || "—"],
      ["Links", String(degree)],
      ["Came in", event ? arrivalName(event.sourceArrival) : "—"],
      ["Independence", event ? independenceName(event.independence) : "—"],
    ];
    if (previous) recordRows.push(["Relation", step ? RELATION_LABEL[step.relation] : "—"]);
    const block = document.createElement("details");
    block.className = "opened-note";
    block.dataset.noteId = id;
    const summary = document.createElement("summary");
    const keyword = noteKeyword(event);
    const headline = document.createElement("span");
    headline.className = "headline";
    if (keyword) {
      const word = document.createElement("span");
      word.className = "keyword-tag";
      word.textContent = keyword;
      headline.append(word);
    }
    const tag = document.createElement("span");
    tag.className = "record-tag";
    tag.textContent = event?.id ?? id;
    headline.append(tag);
    summary.append(headline);
    const extra = asideTitle(event?.text ?? "", keyword);
    if (extra) {
      const title = document.createElement("span");
      title.className = "note-title";
      title.textContent = extra;
      summary.append(title);
    }
    block.append(summary);
    const body = document.createElement("p");
    body.className = "note-text";
    if (event) body.textContent = event.text;
    else if (pointer) body.textContent = `Record with ${pointer.memberEventIds.length} source notes.`;
    else body.textContent = "No text stored for this note.";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-path";
    copy.textContent = "Copy path";
    copy.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      copyPath(id, copy);
    });
    block.append(body, copy, factFold("Record", recordRows), explorationFold(trail.slice(0, at + 1)));
    block.addEventListener("toggle", () => {
      if (block.open) openBlocks.add(id);
      else openBlocks.delete(id);
    });
    block.open = openBlocks.has(id);
    noteFacts.append(block);
  }
  paintOpenedHover();
}

function factFold(label: string, rows: Array<[string, string]>, routes: string[] = []): HTMLDetailsElement {
  const fold = document.createElement("details");
  fold.className = "note-fold";
  const summary = document.createElement("summary");
  summary.textContent = label;
  fold.append(summary);
  for (const [name, value] of rows) {
    const row = document.createElement("div");
    row.className = "fact";
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = name;
    detail.textContent = value;
    row.append(term, detail);
    fold.append(row);
  }
  if (routes.length > 0) {
    const list = document.createElement("ul");
    list.className = "routes";
    for (const route of routes) {
      const item = document.createElement("li");
      item.textContent = route;
      list.append(item);
    }
    fold.append(list);
  }
  return fold;
}

function explorationFold(path: string[]): HTMLDetailsElement {
  const look = lab.describeTrail(personId, path);
  const marked = (count: number) => `${count} · ${look.counts.countLabel}`;
  return factFold(
    "Exploration",
    [
      ["Hop depth", String(look.page.hopDepth)],
      ["Breadcrumb", look.page.breadcrumb.join(" → ") || "—"],
      ["Direct links", String(look.page.directLinkCount)],
      ["Explored", marked(look.counts.exploredCount)],
      ["Unexplored", marked(look.counts.unexploredCount)],
      ["Reachable", marked(look.counts.reachableCount)],
      ["Cycles", String(look.page.cycleCount)],
      ["Status", look.page.detail],
    ],
    look.page.nextRoutes.map((route) => route.label),
  );
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

function fullMapPlaces(ids: readonly string[]): Map<string, Point> {
  const full = new Map<string, Point>();
  for (const [id, point] of mapPositions) full.set(id, { x: point.x, y: point.y });
  const view = lab.view(personId);
  for (const id of ids) {
    if (full.has(id)) continue;
    const index = view.nodes.findIndex((node) => node.id === id);
    if (index < 0) continue;
    full.set(id, { x: positions[index * 2] ?? 0, y: positions[index * 2 + 1] ?? 0 });
  }
  return full;
}

function lookRadii(ids: readonly string[], sizes: Float32Array): Map<string, number> {
  const radii = new Map<string, number>();
  ids.forEach((id, index) => {
    radii.set(id, (sizes[index] ?? circleSize(0)) / 2);
  });
  return radii;
}

// A few hops should fit on the short side. The circle stays large enough to read.
function lookZoom(): number {
  const canvas = stage.querySelector("canvas");
  const shorter = Math.max(320, Math.min(canvas?.clientWidth || 900, canvas?.clientHeight || 700));
  const hopPx = shorter / 5.2;
  const diameter = hopPx / HOP_DIAMETERS;
  return diameter / circleSize(2);
}

function paint(fit: boolean): void {
  driftToken += 1;
  if (!graph) return;
  if (dragHomesFullMap !== showAll) {
    dragHomes.clear();
    dragHomesFullMap = showAll;
  }
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
    const tint = paintColor(rgb, alpha);
    colors.set(tint, index * 4);
    const degree = degrees[index] ?? 0;
    const size = sizes[index] ?? circleSize(0);
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
  if (showAll) {
    settle(pointPositions, pairs, 96, 14, 0.045);
  } else {
    const radii = lookRadii(drawnIds, sizes);
    const latest = trail[trail.length - 1] ?? drawnIds[0] ?? "";
    const placed = growLook({
      stored: lookPositions,
      shownIds: drawnIds,
      latestId: latest,
      fullMap: fullMapPlaces(drawnIds),
      radii,
      origin: { x: SPACE_SIZE / 2, y: SPACE_SIZE / 2 },
    });
    lookPositions.clear();
    for (const [id, point] of placed) lookPositions.set(id, point);
    drawnIds.forEach((id, index) => {
      const point = lookPositions.get(id);
      if (!point) return;
      pointPositions[index * 2] = point.x;
      pointPositions[index * 2 + 1] = point.y;
    });
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
    clearCrossings(pointPositions, pairs, sizes, 8);
    spreadCircles(pointPositions, sizes);
    mapPositions.clear();
    drawnIds.forEach((id, index) => {
      mapPositions.set(id, { x: pointPositions[index * 2] ?? 0, y: pointPositions[index * 2 + 1] ?? 0 });
    });
    lookPositions.clear();
    frozenScale = null;
  }
  drawnIds.forEach((id, index) => {
    const home = dragHomes.get(id);
    if (!home) return;
    pointPositions[index * 2] = home.x;
    pointPositions[index * 2 + 1] = home.y;
    if (showAll) mapPositions.set(id, home);
    else lookPositions.set(id, home);
  });
  labelState.forEach((item, index) => {
    item.x = pointPositions[index * 2] ?? item.x;
    item.y = pointPositions[index * 2 + 1] ?? item.y;
  });
  let drawPositions = pointPositions;
  if (!showAll) {
    // Positions are already in space units, one unit per circle-size unit.
    // Squeezing them into a fitted box made every link a large slice of the screen.
    if (!frozenScale) frozenScale = { x: (value) => value, y: (value) => value };
    const scale = frozenScale;
    drawPositions = new Float32Array(pointPositions.length);
    for (let index = 0; index < pointPositions.length; index += 2) {
      drawPositions[index] = scale.x(pointPositions[index] ?? 0);
      drawPositions[index + 1] = scale.y(pointPositions[index + 1] ?? 0);
    }
    graph.setPointPositions(drawPositions, true);
  } else {
    graph.setPointPositions(pointPositions, !fit);
  }
  graph.setPointColors(colors);
  graph.setPointSizes(sizes);
  graph.setLinks(links);
  graph.setLinkColors(linkColors);
  graph.setLinkWidths(linkWidths);
  graph.setLinkStyles(linkStyles);
  graph.render(undefined, 0);
  focusOpenedNote();
  if (fit && drawPositions.length > 0) fitPicture(drawPositions);
  else {
    fitToken += 1;
    placeDegreeLabels();
    if (drawPositions.length > 0) driftAround(Array.from(drawPositions));
  }
}

function focusOpenedNote(): void {
  if (!graph) return;
  const index = !showAll && selectedId ? drawnIds.indexOf(selectedId) : -1;
  graph.setConfigPartial({ focusedPointIndex: index >= 0 ? index : undefined });
}

function fitPicture(pointPositions: Float32Array): void {
  const token = ++fitToken;
  const opened = !showAll;
  const positions = Array.from(pointPositions);
  const apply = (): void => {
    if (!graph || token !== fitToken) return;
    if (opened) graph.setZoomTransformByPointPositions(Float32Array.from(positions), 0, lookZoom(), 0.2, false);
    else graph.fitViewByPointPositions(positions, 0, 0.2, false);
  };
  apply();
  requestAnimationFrame(() => {
    if (token !== fitToken) return;
    apply();
    requestAnimationFrame(() => {
      if (token !== fitToken) return;
      placeDegreeLabels();
      driftAround(positions);
    });
  });
}

// Radius of the disc Cosmos actually draws, in the same units as the positions.
function drawnRadii(): Float32Array {
  const radii = new Float32Array(labelState.length);
  if (!graph) return radii;
  const [x0, y0] = graph.spaceToScreenPosition([0, 0]);
  const [x1, y1] = graph.spaceToScreenPosition([100, 0]);
  const pixelsPerUnit = Math.hypot(x1 - x0, y1 - y0) / 100;
  const unit = pixelsPerUnit > 1e-4 ? 1 / pixelsPerUnit : 1;
  for (let index = 0; index < labelState.length; index += 1) {
    const size = labelState[index]?.size ?? circleSize(0);
    radii[index] = (fillDiameter(size) / 2 + 3) * unit;
  }
  return radii;
}

// Push only pairs whose discs cover each other, until the edges clear.
// A placed circle stays where it was put. The other circle takes the whole push.
function separateOverlaps(flat: Float32Array, radii: Float32Array, pinned: ReadonlySet<number>): void {
  const count = radii.length;
  const pad = 6;
  for (let pass = 0; pass < 32; pass += 1) {
    let moved = false;
    for (let left = 0; left < count; left += 1) {
      for (let right = left + 1; right < count; right += 1) {
        const leftPinned = pinned.has(left);
        const rightPinned = pinned.has(right);
        if (leftPinned && rightPinned) continue;
        let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
        let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
        let dist = Math.hypot(dx, dy);
        const min = (radii[left] ?? 0) + (radii[right] ?? 0) + pad;
        if (dist >= min) continue;
        if (dist < 1e-4) {
          const angle = (left + 1) * mapSettings.turn;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          dist = 1;
        }
        const share = leftPinned || rightPinned ? 1 : 0.5;
        const push = (min - dist) * share;
        const ux = (dx / dist) * push;
        const uy = (dy / dist) * push;
        if (!leftPinned) {
          flat[left * 2] = (flat[left * 2] ?? 0) - ux;
          flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) - uy;
        }
        if (!rightPinned) {
          flat[right * 2] = (flat[right * 2] ?? 0) + ux;
          flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) + uy;
        }
        moved = true;
      }
    }
    if (!moved) break;
  }
}

// Float around the stored layout, then separate any discs that would cover.
function driftAround(home: number[]): void {
  const token = ++driftToken;
  const anchor = Float32Array.from(home);
  driftAnchor = anchor;
  frozenScale = { x: (value) => value, y: (value) => value };
  const started = performance.now();
  const frame = (now: number): void => {
    if (token !== driftToken || !graph) return;
    const elapsed = (now - started) / 1000;
    const pinned = new Set<number>();
    if (draggingIndex !== null) pinned.add(draggingIndex);
    drawnIds.forEach((id, index) => {
      if (dragHomes.has(id)) pinned.add(index);
    });
    const drifted = new Float32Array(anchor.length);
    for (let index = 0; index < labelState.length; index += 1) {
      const phase = index * mapSettings.turn;
      const held = draggingIndex === index ? dragPoint : null;
      drifted[index * 2] = held ? held.x : (anchor[index * 2] ?? 0) + Math.sin(elapsed * 0.55 + phase) * 9;
      drifted[index * 2 + 1] = held ? held.y : (anchor[index * 2 + 1] ?? 0) + Math.cos(elapsed * 0.4 + phase) * 9;
    }
    separateOverlaps(drifted, drawnRadii(), pinned);
    if (draggingIndex !== null && dragPoint) {
      drifted[draggingIndex * 2] = dragPoint.x;
      drifted[draggingIndex * 2 + 1] = dragPoint.y;
    }
    for (let index = 0; index < labelState.length; index += 1) {
      const item = labelState[index];
      if (!item) continue;
      item.x = drifted[index * 2] ?? item.x;
      item.y = drifted[index * 2 + 1] ?? item.y;
    }
    graph.setPointPositions(drifted, true);
    graph.render(undefined, 0);
    syncLabelMotion();
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
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
      mapPositions.clear();
      lookPositions.clear();
      dragHomes.clear();
      frozenScale = null;
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
  lookPositions.clear();
  dragHomes.clear();
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
  const weight = mapSettings.curve.weight;
  const x = remain * remain * start.x + 2 * remain * t * weight * control.x + t * t * end.x;
  const y = remain * remain * start.y + 2 * remain * t * weight * control.y + t * t * end.y;
  const divisor = remain * remain + 2 * remain * t * weight + t * t;
  return { x: x / divisor, y: y / divisor };
}

let hoveredId: string | null = null;

function paintOpenedHover(): void {
  for (const block of noteFacts.querySelectorAll<HTMLElement>(".opened-note")) {
    block.classList.toggle("is-hovered", hoveredId !== null && block.dataset.noteId === hoveredId);
  }
}

function highlightOpened(id: string | null): void {
  hoveredId = id;
  paintOpenedHover();
  paintHoverId();
}

let pointerOverMap: { x: number; y: number } | null = null;
let driftAnchor: Float32Array | null = null;
let draggingIndex: number | null = null;
let dragPoint: { x: number; y: number } | null = null;
let suppressClick = false;
const dragHomes = new Map<string, Point>();
let dragHomesFullMap = true;
let grab: { pointerId: number; index: number; id: string; x: number; y: number } | null = null;
let press: { id: string; dragged: boolean } | null = null;

function circleUnder(x: number, y: number): { id: string; index: number } | null {
  let next: string | null = null;
  let closest = Infinity;
  for (const [id, spot] of labelSpots) {
    const distance = Math.hypot(spot.x - x, spot.y - y);
    if (distance <= spot.radius + 3 && distance < closest) {
      next = id;
      closest = distance;
    }
  }
  if (!next) return null;
  const index = drawnIds.indexOf(next);
  return index < 0 ? null : { id: next, index };
}

function pointerOnLayer(event: PointerEvent): { x: number; y: number } {
  const layer = degreeLabels.getBoundingClientRect();
  return { x: event.clientX - layer.left, y: event.clientY - layer.top };
}

function spaceFromPointer(event: PointerEvent): { x: number; y: number } | null {
  if (!graph) return null;
  const canvas = stage.querySelector("canvas");
  if (!canvas) return null;
  const box = canvas.getBoundingClientRect();
  const [x, y] = graph.screenToSpacePosition([event.clientX - box.left, event.clientY - box.top]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x, y };
}

function holdDrag(index: number, id: string, point: { x: number; y: number }): void {
  draggingIndex = index;
  dragPoint = point;
  if (driftAnchor) {
    driftAnchor[index * 2] = point.x;
    driftAnchor[index * 2 + 1] = point.y;
  }
  const home = { x: point.x, y: point.y };
  dragHomes.set(id, home);
  if (showAll) mapPositions.set(id, home);
  else lookPositions.set(id, home);
}

function finishDrag(): void {
  draggingIndex = null;
  dragPoint = null;
  grab = null;
  stage.style.cursor = "";
}

function openCircle(id: string): void {
  const keepCamera = !showAll && lookPositions.size > 0;
  if (!openNote(id)) return;
  paint(!keepCamera);
}

function placeFromPointer(event: PointerEvent): void {
  if (!grab || event.pointerId !== grab.pointerId) return;
  if (Math.hypot(event.clientX - grab.x, event.clientY - grab.y) < 4) return;
  suppressClick = true;
  if (press) press.dragged = true;
  const space = spaceFromPointer(event);
  if (!space) return;
  holdDrag(grab.index, grab.id, space);
  stage.style.cursor = "grabbing";
}

function hoverFromPointer(): void {
  if (!pointerOverMap || grab) return;
  const hit = circleUnder(pointerOverMap.x, pointerOverMap.y);
  const next = hit?.id ?? null;
  if (next !== hoveredId) highlightOpened(next);
  stage.style.cursor = next ? "grab" : "";
}

// The drift redraws the map every frame, which keeps Cosmos from settling its own hover.
// Hit-testing the circles ourselves keeps the id, the ring, and the drag.
stage.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  const layerPoint = pointerOnLayer(event);
  const hit = circleUnder(layerPoint.x, layerPoint.y);
  if (!hit) return;
  grab = { pointerId: event.pointerId, index: hit.index, id: hit.id, x: event.clientX, y: event.clientY };
  press = { id: hit.id, dragged: false };
});
stage.addEventListener("pointermove", (event) => {
  pointerOverMap = pointerOnLayer(event);
  if (grab && event.pointerId === grab.pointerId) placeFromPointer(event);
  else hoverFromPointer();
});
stage.addEventListener("pointerup", (event) => {
  if (grab && event.pointerId !== grab.pointerId) return;
  const id = press?.id ?? grab?.id;
  const dragged = suppressClick || press?.dragged === true;
  finishDrag();
  press = null;
  if (!id || dragged) {
    if (dragged) window.setTimeout(() => {
      suppressClick = false;
    }, 0);
    return;
  }
  suppressClick = true;
  openCircle(id);
  window.setTimeout(() => {
    suppressClick = false;
  }, 0);
});
stage.addEventListener("pointercancel", (event) => {
  if (!grab || event.pointerId !== grab.pointerId) return;
  finishDrag();
  press = null;
});
stage.addEventListener("pointerleave", () => {
  if (grab) return;
  pointerOverMap = null;
  highlightOpened(null);
  stage.style.cursor = "";
});

function fillDiameter(size: number): number {
  if (!graph) return size;
  // Cosmos draws the fill as size × zoom, up to the hardware point-size limit.
  // The ring, the digit, and the link end use that same diameter.
  return Math.min(size * graph.getZoomLevel(), pointSizeCap());
}

function pointSizeCap(): number {
  const canvas = stage.querySelector("canvas");
  const gl = canvas?.getContext("webgl2") ?? canvas?.getContext("webgl");
  const ratio = window.devicePixelRatio || 1;
  if (!gl) return 64;
  const range = gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE) as [number, number] | null;
  const hardware = range?.[1] ?? 64 * ratio;
  return hardware / ratio;
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
      x: (start.x + end.x) / 2 + (-dy / length) * length * mapSettings.curve.control,
      y: (start.y + end.y) / 2 + (dx / length) * length * mapSettings.curve.control,
    };
    const samples: Array<{ x: number; y: number; open: boolean }> = [];
    for (let index = 0; index <= 32; index += 1) {
      const point = conicPoint(start, end, control, index / 32);
      const [sx, sy] = graph.spaceToScreenPosition([point.x, point.y]);
      const x = offsetX + sx;
      const y = offsetY + sy;
      const blocked = [...screen.values()].some(
        (spot) => Math.hypot(x - spot.x, y - spot.y) < spot.radius + 2,
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

function labelScreens(): {
  screen: Map<string, { x: number; y: number; radius: number }>;
  space: Map<string, { x: number; y: number }>;
  offsetX: number;
  offsetY: number;
  canvas: HTMLCanvasElement;
} | null {
  if (!graph || labelState.length === 0) return null;
  const canvas = stage.querySelector("canvas");
  if (!canvas) return null;
  const canvasBox = canvas.getBoundingClientRect();
  const layerBox = degreeLabels.getBoundingClientRect();
  const offsetX = canvasBox.left - layerBox.left;
  const offsetY = canvasBox.top - layerBox.top;
  const flat = new Float32Array(labelState.length * 2);
  labelState.forEach((item, index) => {
    flat[index * 2] = item.x;
    flat[index * 2 + 1] = item.y;
  });
  const rescale = frozenScale ?? rescaleToSpace(flat);
  const screen = new Map<string, { x: number; y: number; radius: number }>();
  const space = new Map<string, { x: number; y: number }>();
  for (const item of labelState) {
    const diameter = fillDiameter(item.size);
    const x = rescale.x(item.x);
    const y = rescale.y(item.y);
    const [sx, sy] = graph.spaceToScreenPosition([x, y]);
    screen.set(item.id, { x: offsetX + sx, y: offsetY + sy, radius: diameter / 2 });
    space.set(item.id, { x, y });
  }
  return { screen, space, offsetX, offsetY, canvas };
}

// One size for every keyword: a word of fittedLetters still fits in the smallest circle.
function sharedKeywordFont(screen: Map<string, { radius: number }>): number {
  const keyword = mapSettings.keyword;
  let smallest = Infinity;
  for (const spot of screen.values()) {
    const diameter = spot.radius * 2;
    if (diameter >= keyword.minDiameter && diameter < smallest) smallest = diameter;
  }
  if (!Number.isFinite(smallest)) return keyword.fallbackPx;
  return (smallest * keyword.fillOfDiameter) / (keyword.fittedLetters * keyword.charWidthRatio);
}

function placeRing(id: string, spot: { x: number; y: number; radius: number }, origin: string | undefined): void {
  const ring = document.createElement("i");
  ring.className = id === origin ? "trail-ring is-start" : "trail-ring";
  ring.dataset.noteId = id;
  const box = spot.radius * 2 + Math.max(6, spot.radius * 0.08);
  ring.style.left = `${spot.x}px`;
  ring.style.top = `${spot.y}px`;
  ring.style.width = `${box}px`;
  ring.style.height = `${box}px`;
  ring.style.borderWidth = `${Math.max(3, spot.radius * 0.06)}px`;
  degreeLabels.appendChild(ring);
}

function placeDegreeLabels(): void {
  degreeLabels.replaceChildren();
  const placed = labelScreens();
  if (!placed) return;
  const { screen, space, offsetX, offsetY, canvas } = placed;
  placeMovingPipes(space, screen, offsetX, offsetY);
  const origin = trail[0];
  const earlier = new Set(trail.slice(0, -1));
  for (const item of labelState) {
    const isOrigin = item.id === origin;
    if (!isOrigin && !earlier.has(item.id)) continue;
    const spot = screen.get(item.id);
    if (!spot) continue;
    if (spot.x < -20 || spot.y < -20 || spot.x > canvas.clientWidth + 20 || spot.y > canvas.clientHeight + 20) continue;
    placeRing(item.id, spot, origin);
  }
  labelSpots = screen;
  const font = sharedKeywordFont(screen);
  for (const item of labelState) {
    const spot = screen.get(item.id);
    if (!spot) continue;
    const word = noteKeyword(lab.vault.get(item.id));
    if (!word) continue;
    if (spot.radius * 2 < 8) continue;
    if (spot.x < -20 || spot.y < -20 || spot.x > canvas.clientWidth + 20 || spot.y > canvas.clientHeight + 20) continue;
    const label = document.createElement("span");
    label.className = "memory-word";
    label.dataset.noteId = item.id;
    label.textContent = word;
    label.style.left = `${spot.x}px`;
    label.style.top = `${spot.y}px`;
    label.style.fontSize = `${font}px`;
    label.style.fontWeight = "400";
    degreeLabels.appendChild(label);
  }
  paintHoverId();
}

function syncLabelMotion(): void {
  const placed = labelScreens();
  if (!placed) return;
  const { screen, space, offsetX, offsetY } = placed;
  labelSpots = screen;
  const words = degreeLabels.querySelectorAll<HTMLElement>(".memory-word");
  if (words.length === 0) {
    placeDegreeLabels();
    return;
  }
  for (const word of words) {
    const spot = word.dataset.noteId ? screen.get(word.dataset.noteId) : undefined;
    if (!spot) continue;
    word.style.left = `${spot.x}px`;
    word.style.top = `${spot.y}px`;
  }
  for (const ring of degreeLabels.querySelectorAll<HTMLElement>(".trail-ring")) {
    const spot = ring.dataset.noteId ? screen.get(ring.dataset.noteId) : undefined;
    if (!spot) continue;
    const box = spot.radius * 2 + Math.max(6, spot.radius * 0.08);
    ring.style.left = `${spot.x}px`;
    ring.style.top = `${spot.y}px`;
    ring.style.width = `${box}px`;
    ring.style.height = `${box}px`;
    ring.style.borderWidth = `${Math.max(3, spot.radius * 0.06)}px`;
  }
  degreeLabels.querySelector(".pipe-flow")?.remove();
  placeMovingPipes(space, screen, offsetX, offsetY);
  const spot = hoveredId ? screen.get(hoveredId) : undefined;
  const ring = degreeLabels.querySelector<HTMLElement>(".hover-ring");
  const mark = degreeLabels.querySelector<HTMLElement>(".hover-id");
  if (spot && ring && mark) {
    const box = spot.radius * 2 + 8;
    ring.style.left = `${spot.x}px`;
    ring.style.top = `${spot.y}px`;
    ring.style.width = `${box}px`;
    ring.style.height = `${box}px`;
    mark.style.left = `${spot.x}px`;
    mark.style.top = `${spot.y - spot.radius - 18}px`;
  }
  hoverFromPointer();
}

let labelSpots = new Map<string, { x: number; y: number; radius: number }>();

function paintHoverId(): void {
  degreeLabels.querySelector(".hover-id")?.remove();
  degreeLabels.querySelector(".hover-ring")?.remove();
  if (!hoveredId) return;
  const spot = labelSpots.get(hoveredId);
  if (!spot) return;
  const ring = document.createElement("i");
  ring.className = "hover-ring";
  const box = spot.radius * 2 + 8;
  ring.style.left = `${spot.x}px`;
  ring.style.top = `${spot.y}px`;
  ring.style.width = `${box}px`;
  ring.style.height = `${box}px`;
  degreeLabels.append(ring);
  const mark = document.createElement("span");
  mark.className = "hover-id";
  mark.textContent = lab.vault.get(hoveredId)?.id ?? hoveredId;
  mark.style.left = `${spot.x}px`;
  mark.style.top = `${spot.y - spot.radius - 18}px`;
  degreeLabels.append(mark);
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

function copyPath(throughId: string, control?: HTMLButtonElement): void {
  const end = trail.indexOf(throughId);
  if (end < 0) return;
  const text = trail
    .slice(0, end + 1)
    .map((id) => lab.vault.get(id)?.id ?? id)
    .join(", ");
  const confirm = (): void => {
    if (!control) return;
    control.textContent = "Copied";
    window.setTimeout(() => {
      if (control.textContent === "Copied") control.textContent = "Copy path";
    }, 1600);
  };
  const fallback = (): void => {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
    confirm();
  };
  if (!navigator.clipboard?.writeText) {
    fallback();
    return;
  }
  void navigator.clipboard.writeText(text).then(confirm).catch(fallback);
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
  mapPositions.clear();
  lookPositions.clear();
  dragHomes.clear();
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
