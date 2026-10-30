import { MAP_MOTION, type MapMotionConfig } from "./config";
type Point = { x: number; y: number };
export type PebblePoseInput = {
  now: number; radius: number; calm: boolean; hot: boolean; grabbed: boolean;
  lean?: Point; movement?: Point; lift: number; phase: number; screenScale?: number;
  emphasis?: 'hover' | 'selected'; maxScale?: number;
};

/** Aim for 1.6 CSS pixels of edge travel, bounded for tiny and very large objects. */
export function pebbleBreathAmplitude(screenRadius: number, config: Readonly<MapMotionConfig> = MAP_MOTION) {
  return Math.max(config.minBreathScale, Math.min(config.maxBreathScale, config.breathTravelPx / Math.max(1, screenRadius)));
}

/** Measure outside the animated body so breathing cannot feed back into its amplitude. */
export function pebbleScreenScale(element: SVGGraphicsElement | null) {
  const matrix = element?.getScreenCTM?.();
  return matrix ? Math.max(Math.hypot(matrix.a, matrix.b), Math.hypot(matrix.c, matrix.d)) : 1;
}

/** A bounded material response within the map's reserved layout clearance. */
export class PebbleMotion {
  constructor(private config: Readonly<MapMotionConfig> = MAP_MOTION) {}
  private turn = 0;
  private stretch = 0;
  private time = 0;
  private lightX = 0;
  private lightY = 0;
  private emphasis = 0;
  private dragDirection: Point = { x: 1, y: 0 };

  paint(root: SVGGElement, input: PebblePoseInput) {
    const { now, calm, grabbed, hot, radius, phase, lift } = input;
    const dt = Math.min(64, Math.max(0, now - this.time || 16));
    this.time = now;
    const ease = calm ? 1 : 1 - Math.exp(-dt / this.config.poseSettleMs);
    const lean = input.lean ?? { x: 0, y: 0 };
    const movement = input.movement ?? { x: 0, y: 0 };
    const travel = Math.hypot(movement.x, movement.y);
    if (grabbed && travel > 0.1) this.dragDirection = { x: movement.x / travel, y: movement.y / travel };
    const targetTurn = calm ? 0 : grabbed ? this.dragDirection.x * 9 + this.dragDirection.y * 2 : hot ? lean.x * 7 + 2 : Math.sin(now * 0.00043 + phase) * 1.4;
    this.turn += (targetTurn - this.turn) * ease;
    this.stretch += ((calm ? 0 : grabbed ? Math.min(this.config.maxDragStretch, 0.012 + travel * 0.0018) : 0) - this.stretch) * ease;
    this.lightX += ((calm ? 0 : lean.x * 7 + this.turn * 0.35) - this.lightX) * ease;
    this.lightY += ((calm ? 0 : lean.y * 5) - this.lightY) * ease;
    // Density, responsive sizing and zoom all affect the visible radius.
    const amplitude = pebbleBreathAmplitude(radius * (input.screenScale ?? 1), this.config);
    const targetEmphasis = input.emphasis === 'selected' ? this.config.selectedScale - 1 : input.emphasis === 'hover' ? this.config.hoverScale - 1 : 0;
    const emphasisEase = calm ? 1 : 1 - Math.exp(-dt / this.config.emphasisSettleMs);
    if (!grabbed) this.emphasis += (targetEmphasis - this.emphasis) * emphasisEase;
    const activation = Math.min(1, this.emphasis / Math.max(0.001, this.config.hoverScale - 1));
    const breath = calm || grabbed ? 0 : Math.sin(now * (Math.PI * 2 / this.config.breathDurationMs) + phase) * amplitude * (1 - activation * (1 - this.config.activeBreathFactor));
    const scale = Math.min(input.maxScale ?? Infinity, 1 + this.emphasis + breath);
    const direction = this.dragDirection;
    const scaleX = scale + this.stretch * (direction.x ** 2 - direction.y ** 2 * 0.7);
    const scaleY = scale + this.stretch * (direction.y ** 2 - direction.x ** 2 * 0.7);
    const shear = this.stretch * 1.7 * direction.x * direction.y;
    const pose = calm ? `rotate(0) scale(${scale} ${scale})` : `rotate(${this.turn.toFixed(3)}) matrix(${scaleX.toFixed(4)} ${shear.toFixed(4)} ${shear.toFixed(4)} ${scaleY.toFixed(4)} 0 0)`;
    root.querySelectorAll<SVGGElement>('[data-pebble-body], [data-pebble-face]').forEach((element) => element.setAttribute("transform", pose));
    const light = root.querySelector<SVGRadialGradientElement>('[data-pebble-light]');
    light?.setAttribute("cx", `${28 + this.lightX}%`);
    light?.setAttribute("cy", `${18 + this.lightY}%`);
    light?.setAttribute("fx", `${25 + this.lightX}%`);
    light?.setAttribute("fy", `${15 + this.lightY}%`);
    root.querySelectorAll<SVGFEPointLightElement>('[data-pebble-lamp]').forEach((lamp) => {
      lamp.setAttribute("x", String(-130 + this.lightX * 4));
      lamp.setAttribute("y", String(-170 + this.lightY * 4));
    });
    const glint = root.querySelector<SVGEllipseElement>('[data-highlight]');
    glint?.setAttribute("transform", `translate(${this.lightX * 0.75} ${this.lightY * 0.65}) rotate(${42 - this.turn * 0.3} -43 -57)`);
    const ground = root.querySelector<SVGGElement>('[data-pebble-ground]');
    ground?.setAttribute("transform", `translate(${grabbed ? this.turn * radius * 0.006 : 0} ${lift})`);
    const shadow = root.querySelector<SVGEllipseElement>('[data-pebble-shadow]');
    shadow?.setAttribute("rx", String(radius * (0.88 + lift * 0.015) * (1 + (scale - 1) * 0.7)));
    shadow?.setAttribute("opacity", String(0.25 - lift * 0.008));
    root.querySelector('[data-pebble-contact]')?.setAttribute("opacity", String(Math.max(0.06, 0.21 - lift * 0.018)));
    root.setAttribute("data-pebble-pose", calm ? "still" : grabbed ? "drag" : hot ? "hover" : "rest");
    root.setAttribute("data-pebble-scale", scale.toFixed(4));
    const emphasisScale = (1 + this.emphasis).toFixed(4);
    if (root.getAttribute('data-pebble-emphasis-scale') !== emphasisScale) root.setAttribute('data-pebble-emphasis-scale', emphasisScale);
  }
}
