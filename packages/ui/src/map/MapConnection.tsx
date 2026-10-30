"use client";

import { useId, useLayoutEffect, useRef, type CSSProperties } from "react";
import { SilkLink, type SilkFrame, type SilkPoint } from "./core";
import { porcelainTint } from "./core/material";
import { subscribeMapFrame } from "./core/frameClock";
import { MAP_LINK, type MapLinkConfig } from "./core/config";
import styles from "./MapVisuals.module.css";

export type MapConnectionProps = SilkFrame & {
  id: string;
  source: string;
  target: string;
  stroke: string;
  endStroke: string;
  sourceSegment?: string;
  targetSegment?: string;
  relationship?: string;
  material?: Partial<MapLinkConfig>;
  width: number;
  opacity: number;
  faded: boolean;
  dash?: string;
  active: boolean;
  flow: boolean;
  onSelect?: () => void;
  /** Optional live scene geometry for maps with imperative placement. Routing policy remains caller-owned. */
  getFrame?: () => SilkFrame;
};

/** One shared geometry drives the visible stroke, selection hit area, and sheen. */
export function MapConnection(props: MapConnectionProps) {
  const paintId = `silk-${useId().replace(/:/g, "")}`;
  const group = useRef<SVGGElement>(null);
  const state = useRef<SilkLink | null>(null);
  if (!state.current) state.current = new SilkLink(props.id);
  const latest = useRef(props);
  latest.current = props;
  const repaint = useRef<() => void>(() => {});

  useLayoutEffect(() => {
    const animated = !latest.current.calm && typeof requestAnimationFrame === "function";
    const circles = new Map<string, SVGCircleElement>();
    const actualPoint = (id: string, point: SilkPoint, calm: boolean): SilkPoint => {
      const svg = group.current?.ownerSVGElement;
      if (!svg || typeof group.current?.getCTM !== "function") return point;
      let circle = circles.get(id);
      if (!circle?.isConnected) {
        const node = [...svg.querySelectorAll('[data-map-object-id]')].find((element) => element.getAttribute("data-map-object-id") === id);
        circle = node?.querySelector<SVGCircleElement>('[data-pebble-bounds]') ?? node?.querySelector<SVGCircleElement>('circle') ?? undefined;
        if (circle) circles.set(id, circle);
      }
      const scale = Number(circle?.closest('[data-pebble-object]')?.getAttribute('data-pebble-scale') ?? 1);
      const r = point.r * scale;
      // Reduced motion uses authoritative layout centers, with instant static
      // emphasis. Only moving material needs potentially changing screen CTMs.
      if (calm) return { ...point, r };
      const matrix = circle?.getCTM();
      const local = group.current?.getCTM();
      if (!circle || !matrix || !local) return point;
      const center = new DOMPoint(Number(circle.getAttribute("cx") ?? 0), Number(circle.getAttribute("cy") ?? 0)).matrixTransform(matrix).matrixTransform(local.inverse());
      return { ...point, r, x: center.x, y: center.y, labelTop: (point.labelTop ?? point.r + 1) + point.y - center.y, labelBottom: (point.labelBottom ?? point.r + 34) + point.y - center.y };
    };
    const paint = (now = performance.now()) => {
      const model = { ...latest.current, ...latest.current.getFrame?.() };
      const calm = model.calm || typeof requestAnimationFrame !== "function";
      // A still material has no pose displacement. Its layout coordinates are
      // authoritative, including during a responsive SVG/viewBox commit when
      // getCTM can still describe the preceding frame. Animated material needs
      // its live painted center to keep links attached through lift and drift.
      const a = actualPoint(model.source, model.a, calm);
      const b = actualPoint(model.target, model.b, calm);
      const d = state.current!.frame(now, { ...model, a, b, calm });
      const ports = state.current!.endpoints;
      group.current?.setAttribute('data-source-port-x', String(ports.a.x));
      group.current?.setAttribute('data-source-port-y', String(ports.a.y));
      group.current?.setAttribute('data-target-port-x', String(ports.b.x));
      group.current?.setAttribute('data-target-port-y', String(ports.b.y));
      const gradient = group.current?.querySelector("linearGradient");
      // Anchor the color to the moving endpoints, independently of the curve's bounds.
      gradient?.setAttribute("x1", String(a.x));
      gradient?.setAttribute("y1", String(a.y));
      gradient?.setAttribute("x2", String(b.x));
      gradient?.setAttribute("y2", String(b.y));
      group.current?.querySelectorAll<SVGPathElement>("path").forEach((path) => path.setAttribute("d", d));
      group.current?.setAttribute("data-route-plans", String(state.current!.plans));
    };
    repaint.current = paint;
    paint();
    const scene = group.current?.ownerSVGElement;
    const unsubscribe = animated && scene ? subscribeMapFrame(scene, paint, -10) : () => {};
    const observer = !animated && scene && typeof MutationObserver !== 'undefined' ? new MutationObserver(() => paint()) : null;
    observer?.observe(scene!, { subtree: true, attributes: true, attributeFilter: ['data-pebble-scale', 'data-pebble-x', 'data-pebble-y'] });
    return () => { unsubscribe(); observer?.disconnect(); repaint.current = () => {}; };
  }, [props.calm]);
  useLayoutEffect(() => { repaint.current(); });

  const material = { ...MAP_LINK, ...props.material };
  const stroke = `url(#${paintId})`;
  const delay = -[...props.id].reduce((sum, character) => sum + character.charCodeAt(0), 0) % 55 / 10;
  return <g ref={group} opacity={props.faded ? 0.16 : 1} data-silk-link="" data-highlighted={props.active} data-source={props.source} data-target={props.target} data-source-segment={props.sourceSegment} data-target-segment={props.targetSegment} data-relationship={props.relationship} style={{ "--map-link-glow-blur": `${material.glowBlur}px`, "--map-link-glow-duration": `${material.glowPeriodMs}ms` } as CSSProperties}>
    <defs>
      <linearGradient id={paintId} gradientUnits="userSpaceOnUse" x1={props.a.x} y1={props.a.y} x2={props.b.x} y2={props.b.y}>
        <stop offset="0" stopColor={porcelainTint(props.stroke, material.tint)} />
        <stop offset="1" stopColor={porcelainTint(props.endStroke, material.tint)} />
      </linearGradient>
    </defs>
    <path data-link-glow="" className={styles.linkGlow} fill="none" stroke={stroke} strokeWidth={props.width + (props.active ? 4 : 2.5)} strokeOpacity={props.active ? 0.22 : 0.08} strokeDasharray={props.dash} strokeLinecap="round" pointerEvents="none" vectorEffect="non-scaling-stroke" style={{ animationDelay: `${delay}s`, animation: props.calm ? "none" : undefined }} />
    <path data-connection="" data-source={props.source} data-target={props.target} className={styles.edge} fill="none" stroke={stroke} strokeWidth={props.width * 0.9} strokeOpacity={props.active ? Math.min(0.82, props.opacity * 0.82 + 0.1) : props.opacity * 0.82} strokeDasharray={props.dash} strokeLinecap="round" vectorEffect="non-scaling-stroke" onClick={(event) => { event.stopPropagation(); props.onSelect?.(); }} />
    <path data-link-reflection="" fill="none" stroke="#ffffff" strokeWidth={material.reflectionWidth} strokeOpacity={props.active ? 0.45 : 0.25} strokeDasharray={props.dash} strokeLinecap="round" vectorEffect="non-scaling-stroke" pointerEvents="none" />
    <path fill="none" stroke="transparent" strokeWidth={material.hitWidth} style={{ cursor: "pointer" }} onClick={(event) => { event.stopPropagation(); props.onSelect?.(); }} />
    {props.flow && <path data-link-flow="" className={styles.flow} fill="none" stroke={stroke} pathLength={100} strokeLinecap="round" vectorEffect="non-scaling-stroke" />}
  </g>;
}
