import { porcelainLinkPath } from "./connectionPath";
import type { Point, MapRoutePoint } from "./types";
import { routeInterference } from "./routing";

export type SilkPoint = MapRoutePoint;
export type SilkFrame = {
  a: SilkPoint;
  b: SilkPoint;
  obstacles: readonly SilkPoint[];
  viewport: { width: number; height: number };
  revision: string;
  calm: boolean;
  interacting: boolean;
  hot?: boolean;
  preferredRoute?: { d: string; a: SilkPoint; b: SilkPoint };
  peerRoutes?: readonly (readonly Point[])[];
};
const COUNT = 49;
const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

/** Flatten a planned SVG route once; animated routes always have the same topology. */
export function sampleSilkRoute(d: string): Point[] {
  const tokens = d.match(/[MLCQ]|-?(?:\d*\.)?\d+(?:e[+-]?\d+)?/gi) ?? [];
  const flat: Point[] = [];
  let index = 0;
  let current = { x: 0, y: 0 };
  const point = () => ({ x: Number(tokens[index++]), y: Number(tokens[index++]) });
  while (index < tokens.length) {
    const command = tokens[index++];
    if (command === "M") { current = point(); flat.push(current); }
    else if (command === "L") { current = point(); flat.push(current); }
    else if (command === "C" || command === "Q") {
      const a = current;
      const c1 = point();
      const c2 = command === "C" ? point() : c1;
      const end = point();
      for (let step = 1; step <= 40; step += 1) {
        const t = step / 40, s = 1 - t;
        flat.push(command === "C" ? {
          x: s ** 3 * a.x + 3 * s * s * t * c1.x + 3 * s * t * t * c2.x + t ** 3 * end.x,
          y: s ** 3 * a.y + 3 * s * s * t * c1.y + 3 * s * t * t * c2.y + t ** 3 * end.y,
        } : { x: s * s * a.x + 2 * s * t * c1.x + t * t * end.x, y: s * s * a.y + 2 * s * t * c1.y + t * t * end.y });
      }
      current = end;
    } else throw new Error(`Unsupported silk path command: ${command}`);
  }
  if (!flat.length) return Array.from({ length: COUNT }, () => ({ x: 0, y: 0 }));
  const lengths = [0];
  for (let i = 1; i < flat.length; i += 1) lengths.push(lengths[i - 1]! + distance(flat[i - 1]!, flat[i]!));
  const length = lengths.at(-1)!;
  let cursor = 1;
  return Array.from({ length: COUNT }, (_, i) => {
    const along = length * i / (COUNT - 1);
    while (cursor < lengths.length - 1 && lengths[cursor]! < along) cursor += 1;
    const before = flat[cursor - 1] ?? flat[0]!;
    const after = flat[cursor] ?? before;
    const t = (along - (lengths[cursor - 1] ?? 0)) / ((lengths[cursor] ?? 0) - (lengths[cursor - 1] ?? 0) || 1);
    return { x: before.x + (after.x - before.x) * t, y: before.y + (after.y - before.y) * t };
  });
}

function pathFor(points: readonly Point[]): string {
  const fmt = (value: number) => value.toFixed(2);
  const first = points[0]!;
  let d = `M ${fmt(first.x)} ${fmt(first.y)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const before = points[Math.max(0, i - 1)]!;
    const from = points[i]!;
    const to = points[i + 1]!;
    const after = points[Math.min(points.length - 1, i + 2)]!;
    d += ` C ${fmt(from.x + (to.x - before.x) / 6)} ${fmt(from.y + (to.y - before.y) / 6)}, ${fmt(to.x - (after.x - from.x) / 6)} ${fmt(to.y - (after.y - from.y) / 6)}, ${fmt(to.x)} ${fmt(to.y)}`;
  }
  return d;
}

/** Persistent route + damped material motion. Planning is never an animation frame effect. */
export class SilkLink {
  private plan: Point[] = [];
  private rendered: Point[] = [];
  private bend = 0;
  private bendSpeed = 0;
  private anchorA: SilkPoint | null = null;
  private anchorB: SilkPoint | null = null;
  private obstacleAnchors: readonly SilkPoint[] = [];
  private revision = "";
  private previousA: Point | null = null;
  private previousB: Point | null = null;
  private previousTime = 0;
  private space: { width: number; height: number } | null = null;
  private lastMove = 0;
  private preferred = "";
  readonly phase: number;
  plans = 0;

  get endpoints() { return { a: this.rendered[0]!, b: this.rendered[COUNT - 1]! }; }

  constructor(key: string) {
    this.phase = [...key].reduce((hash, letter) => (hash * 31 + letter.charCodeAt(0)) >>> 0, 7) / 4294967295 * Math.PI * 2;
  }

  /** Carry a route as a shape, preserving its tangents as the chord turns. */
  private carried(a: SilkPoint, b: SilkPoint, plan = this.plan, aa = this.anchorA!, ab = this.anchorB!): Point[] {
    const oldAngle = Math.atan2(ab.y - aa.y, ab.x - aa.x);
    const angle = Math.atan2(b.y - a.y, b.x - a.x) - oldAngle;
    const rotate = (point: Point) => ({ x: point.x * Math.cos(angle) - point.y * Math.sin(angle), y: point.x * Math.sin(angle) + point.y * Math.cos(angle) });
    const first = plan[0]!, last = plan[COUNT - 1]!;
    const scaleA = a.r / (aa.r || a.r || 1), scaleB = b.r / (ab.r || b.r || 1);
    const rimA = rotate({ x: (first.x - aa.x) * scaleA, y: (first.y - aa.y) * scaleA });
    const rimB = rotate({ x: (last.x - ab.x) * scaleB, y: (last.y - ab.y) * scaleB });
    const start = { x: a.x + rimA.x, y: a.y + rimA.y };
    const end = { x: b.x + rimB.x, y: b.y + rimB.y };
    const old = { x: last.x - first.x, y: last.y - first.y };
    const next = { x: end.x - start.x, y: end.y - start.y };
    const denominator = old.x * old.x + old.y * old.y || 1;
    const real = (old.x * next.x + old.y * next.y) / denominator;
    const imaginary = (old.x * next.y - old.y * next.x) / denominator;
    return plan.map((point) => ({ x: start.x + (point.x - first.x) * real - (point.y - first.y) * imaginary, y: start.y + (point.x - first.x) * imaginary + (point.y - first.y) * real }));
  }

  frame(now: number, input: SilkFrame): string {
    const { a, b, calm, interacting } = input;
    const movement = this.previousA && this.previousB ? Math.max(distance(a, this.previousA), distance(b, this.previousB)) : 0;
    if (movement > 0.2 || interacting) this.lastMove = now;
    const proposal = input.preferredRoute?.d ?? "";
    const newPreferred = proposal !== this.preferred && !interacting && (calm || now - this.lastMove > 180);
    const displaced = newPreferred || !this.anchorA || !this.anchorB || Math.max(distance(a, this.anchorA), distance(b, this.anchorB)) > 12 || input.obstacles.length !== this.obstacleAnchors.length || input.obstacles.some((point, i) => !this.obstacleAnchors[i] || distance(point, this.obstacleAnchors[i]!) > 12);
    const newLayout = input.revision !== this.revision;
    // Bounds can grow while dragging without changing the coordinate system.
    // Only an actual layout revision plus resized bounds resets the material.
    const newSpace = newLayout && this.space && (input.viewport.width !== this.space.width || input.viewport.height !== this.space.height);
    if (newSpace) {
      // A resize changes the coordinate system for circles and links together.
      // Never spring from points measured in the previous viewport.
      this.rendered = []; this.bend = 0; this.bendSpeed = 0;
      this.previousA = null; this.previousB = null;
    }
    this.space = { ...input.viewport };
    const settled = !interacting && displaced && (calm || now - this.lastMove > 180);
    const freshPlan = () => {
      const preferred = input.preferredRoute;
      if (preferred && distance(preferred.a, a) < 8 && distance(preferred.b, b) < 8) return this.carried(a, b, sampleSilkRoute(preferred.d), preferred.a, preferred.b);
      const obstacles = input.obstacles.map((point) => ({ ...point, labelWidth: point.labelWidth ?? 100 }));
      return sampleSilkRoute(porcelainLinkPath(a, b, obstacles, 0, input.viewport));
    };
    const quality = (points: readonly Point[]) => points.slice(1).reduce((sum, point, index) => sum + distance(point, points[index]!), 0) + (input.peerRoutes ?? []).reduce((sum, peer) => sum + routeInterference(points, peer), 0);
    let keepRoute = false;
    if (this.plan.length && !newLayout && !newSpace && settled) {
      const carried = this.carried(a, b);
      keepRoute = carried.every((point, i) => {
        if (point.x < 3 || point.x > input.viewport.width - 3 || point.y < 3 || point.y > input.viewport.height - 3) return false;
        return [...input.obstacles, a, b].every((obstacle) => {
          const endpoint = obstacle === a || obstacle === b;
          const circle = !obstacle.labelOnly && (!endpoint || (i > 1 && i < COUNT - 2)) && distance(point, obstacle) < obstacle.r + (endpoint ? -1 : 3);
          const label = !obstacle.allowUnderLabel && Math.abs(point.x - obstacle.x) < (obstacle.labelWidth ?? 100) / 2 + 3 && point.y > obstacle.y + (obstacle.labelTop ?? obstacle.r + 8) - 2 && point.y < obstacle.y + (obstacle.labelBottom ?? obstacle.r + 34) + 2;
          return !circle && !label;
        });
      });
      if (keepRoute) {
        const next = freshPlan();
        // Keep stable clear routes unless a different corridor is materially better.
        // A coordinated scene proposal already includes shared-end geometry
        // and placement costs; a single link must not veto it with a local score.
        this.plan = newPreferred && input.preferredRoute ? next : quality(next) < quality(carried) * 0.9 ? next : carried;
      }
    }
    // A held pointer keeps the route's side and attachment points. Replan once
    // the gesture has settled, and ease the geometry instead of swapping paths.
    if (!this.plan.length || newLayout || newSpace || settled) {
      if (!keepRoute) {
        this.plan = freshPlan();
        this.plans += 1;
      }
      this.anchorA = { ...a }; this.anchorB = { ...b };
      this.obstacleAnchors = input.obstacles.map((point) => ({ ...point }));
      this.revision = input.revision;
      this.preferred = proposal;
    }
    const dt = Math.min(0.032, Math.max(0, (now - this.previousTime) / 1000));
    this.previousTime = now;
    const movementA = this.previousA ? { x: a.x - this.previousA.x, y: a.y - this.previousA.y } : { x: 0, y: 0 };
    const movementB = this.previousB ? { x: b.x - this.previousB.x, y: b.y - this.previousB.y } : { x: 0, y: 0 };
    this.previousA = { ...a }; this.previousB = { ...b };
    const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    const normal = { x: -(b.y - a.y) / length, y: (b.x - a.x) / length };
    const wave = calm ? 0 : Math.sin(now * 0.00085 + this.phase) * (input.hot ? 4.5 : 2.8) + Math.sin(now * 0.0013 + this.phase * 0.7) * 0.8;
    const shape = this.carried(a, b);
    const rimLength = distance(shape[0]!, shape[COUNT - 1]!);
    const limit = Math.min(10, rimLength * 0.05);
    const drive = Math.max(-limit, Math.min(limit, -((movementA.x + movementB.x) * normal.x + (movementA.y + movementB.y) * normal.y) * 2));
    if (calm) { this.bend = 0; this.bendSpeed = 0; }
    else {
      this.bendSpeed += ((drive - this.bend) * 484 - this.bendSpeed * 37) * dt;
      this.bend = Math.max(-limit, Math.min(limit, this.bend + this.bendSpeed * dt));
    }
    for (let i = 0; i < COUNT; i += 1) {
      const t = i / (COUNT - 1);
      const envelope = Math.sin(Math.PI * t) ** 2;
      const rest = shape[i]!;
      // Spring only the bend, not 49 independent positions. The whole route
      // follows its circles immediately, so a short hop cannot create a fold.
      const flex = (Math.max(-limit, Math.min(limit, wave)) + this.bend) * envelope;
      this.rendered[i] = { x: rest.x + normal.x * flex, y: rest.y + normal.y * flex };
    }
    return pathFor(this.rendered);
  }
}
