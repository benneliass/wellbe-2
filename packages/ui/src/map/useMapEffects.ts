"use client";

import { useLayoutEffect, type RefObject } from "react";
import { PebbleMotion, pebbleScreenScale } from "./core";
import { alignSegmentedMaterial } from "./core/alignSegments";
import { subscribeMapFrame } from "./core/frameClock";
import { MAP_MOTION, type MapMotionConfig } from "./core/config";
import { paintMapGroupLights } from './core/paintGroupLights';

/** One clock animates the map's material, without React renders per frame. */
export function useMapEffects(svg: RefObject<SVGSVGElement | null>, reduced: boolean, revision: string, motion: Readonly<MapMotionConfig> = MAP_MOTION) {
  useLayoutEffect(() => {
    const scene = svg.current;
    if (!scene) return;
    const states = new Map<string, { material: PebbleMotion; x: number; y: number; lift: number; time: number; angle: number; orbit: number }>();
    let groupFrame: number | null = null;
    let disposed = false;
    const calm = reduced || typeof requestAnimationFrame !== "function" || (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches);
    const pointer = (event: PointerEvent) => {
      const node = (event.target as Element).closest<SVGGElement>('[data-pebble-node]');
      const circle = node?.querySelector<SVGCircleElement>('[data-pebble-bounds]');
      const matrix = circle?.getScreenCTM?.();
      if (!node || !circle || !matrix || typeof DOMPoint === "undefined") return;
      const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
      const radius = Number(circle.getAttribute("r"));
      node.setAttribute("data-pebble-lean-x", String(Math.max(-1, Math.min(1, p.x / radius))));
      node.setAttribute("data-pebble-lean-y", String(Math.max(-1, Math.min(1, p.y / radius))));
    };
    const paint = (now: number) => {
      const alive = new Set<string>();
      // Objects share the viewport/zoom transform; read it once per frame.
      const screenScale = pebbleScreenScale(scene.querySelector<SVGGElement>('[data-pebble-node]'));
      const links = [...scene.querySelectorAll<SVGGElement>('[data-silk-link]')];
      for (const node of scene.querySelectorAll<SVGGElement>('[data-pebble-node]')) {
        const id = node.getAttribute("data-pebble-key") ?? node.getAttribute("data-map-object-id")!;
        alive.add(id);
        const object = node.querySelector<SVGGElement>('[data-pebble-object]');
        if (!object) continue;
        const x = Number(node.getAttribute("data-pebble-x")), y = Number(node.getAttribute("data-pebble-y"));
        const radius = Number(node.getAttribute("data-pebble-radius"));
        let state = states.get(id);
        if (!state) { state = { material: new PebbleMotion(motion), x, y, lift: 0, time: now, angle: 0, orbit: 0 }; states.set(id, state); }
        const hot = node.getAttribute("data-pebble-hot") === "true";
        const grabbed = node.getAttribute("data-pebble-grabbed") === "true";
        const selected = node.getAttribute("data-map-selected") === "true";
        const ease = calm ? 1 : 1 - Math.exp(-Math.min(64, now - state.time || 16) / motion.positionSettleMs);
        state.lift += ((calm ? 0 : hot ? Math.min(motion.hoverLift, radius * motion.hoverLiftRadius) : 0) - state.lift) * ease;
        const phase = [...id].reduce((sum, character) => sum + character.charCodeAt(0), 0) * 0.37;
        const drift = calm || grabbed ? 0 : Math.sin(now * motion.driftRate + phase) * motion.driftAmplitude;
        object.setAttribute("transform", `translate(0 ${drift - state.lift})`);
        state.material.paint(object, {
          now, radius, calm, hot, grabbed, lift: state.lift - drift, phase, screenScale,
          emphasis: selected ? 'selected' : hot ? 'hover' : undefined,
          lean: hot ? { x: Number(node.getAttribute("data-pebble-lean-x") ?? 0), y: Number(node.getAttribute("data-pebble-lean-y") ?? 0) } : { x: 0, y: 0 },
          movement: { x: x - state.x, y: y - state.y },
        });
        const accents = object.querySelector<SVGGElement>('[data-node-accents]');
        const emphasisScale = Number(object.getAttribute('data-pebble-emphasis-scale') ?? 1);
        const growth = radius * (emphasisScale - 1);
        object.querySelectorAll<SVGGElement>('[data-map-label]').forEach((label) => {
          const lx = Number(label.getAttribute('data-label-anchor-x')), ly = Number(label.getAttribute('data-label-anchor-y'));
          const scale = 1 + (emphasisScale - 1) * motion.labelEmphasisFactor;
          // Names share the object's translation, but stay upright and grow
          // much less than the body so the text remains easy to read.
          label.setAttribute('transform', `translate(${lx} ${ly}) scale(${scale.toFixed(4)}) translate(${-lx} ${-ly})`);
        });
        accents?.querySelector('[data-accent-envelope]')?.setAttribute('transform', `scale(${emphasisScale})`);
        object.querySelectorAll<SVGGElement>('[data-metadata-badge]').forEach((badge) => {
          const bx = Number(badge.getAttribute('data-badge-offset-x')), by = Number(badge.getAttribute('data-badge-offset-y'));
          const scale = 1 + growth / (Math.hypot(bx, by) || 1);
          badge.setAttribute('transform', `translate(${x + bx * scale} ${y + by * scale})`);
        });
        const orbit = accents?.querySelector<SVGGElement>('[data-node-orbit]');
        orbit?.setAttribute('data-orbit-extent', String(Number(orbit.getAttribute('data-orbit-base-extent')) + growth));
        const dt = Math.min(64, Math.max(0, now - state.time));
        if (!calm && !grabbed) {
          state.angle += dt * 360 / Number(accents?.getAttribute('data-accent-period') ?? motion.accentPeriodMs);
          state.orbit += dt * 360 / (motion.orbitMinPeriodMs + phase % 8 * motion.orbitPeriodStepMs);
        }
        const angle = calm ? 0 : state.angle;
        accents?.querySelectorAll<SVGGElement>('[data-accent-rotate]').forEach((element) => {
          element.setAttribute('transform', `rotate(${(angle * Number(element.getAttribute('data-accent-rotate'))).toFixed(3)})`);
        });
        accents?.querySelectorAll<SVGGeometryElement>('[data-accent-sheen]').forEach((element) => element.setAttribute('stroke-dashoffset', String(-angle / 3.6)));
        accents?.querySelectorAll<SVGGElement>('[data-orbit-dot]').forEach((dot) => {
          const a = Number(dot.getAttribute('data-orbit-dot')) + (calm ? 0 : state.orbit * Math.PI / 180);
          const distance = Number(dot.getAttribute('data-orbit-base-radius')) + growth;
          dot.setAttribute('data-orbit-radius', String(distance));
          const x = Math.cos(a) * distance, y = Math.sin(a) * distance;
          dot.setAttribute('data-orbit-x', String(x)); dot.setAttribute('data-orbit-y', String(y));
          dot.setAttribute('transform', `translate(${x} ${y})`);
        });
        if (node.hasAttribute('data-map-segment-keys')) alignSegmentedMaterial(node, links, now, calm || grabbed);
        object.querySelectorAll<SVGCircleElement>('[data-badge-glint]').forEach((glint) => {
          glint.setAttribute('opacity', String(calm ? 0.12 : 0.12 + Math.sin(angle * Math.PI / 90 + phase) * 0.04));
        });
        state.x = x; state.y = y; state.time = now;
      }
      for (const id of states.keys()) if (!alive.has(id)) states.delete(id);
      paintMapGroupLights(scene);
      if (calm && typeof requestAnimationFrame === 'function') {
        if (groupFrame !== null) cancelAnimationFrame(groupFrame);
        groupFrame = requestAnimationFrame(() => { groupFrame = null; paintMapGroupLights(scene); });
      }
    };
    scene.addEventListener("pointermove", pointer, true);
    paint(performance.now());
    document.fonts?.ready.then(() => { if (!disposed) paintMapGroupLights(scene); });
    const unsubscribe = calm ? () => {} : subscribeMapFrame(scene, paint);
    // Reduced motion still needs to repaint after selection, dragging, or a new layout.
    const observer = calm ? new MutationObserver(() => paint(performance.now())) : null;
    observer?.observe(scene, { subtree: true, attributes: true, attributeFilter: ["data-pebble-x", "data-pebble-y", "data-pebble-hot", "data-pebble-grabbed", "data-map-selected", "data-group-layout"], childList: true });
    return () => { disposed = true; unsubscribe(); observer?.disconnect(); if (groupFrame !== null) cancelAnimationFrame(groupFrame); scene.removeEventListener("pointermove", pointer, true); };
  }, [svg, reduced, revision, motion]);
}
