"use client";

import { useLayoutEffect, useRef, type ReactNode, type RefObject } from "react";
import { placeGraphTooltip, type TooltipRect } from "./core/tooltipPlacement";
import styles from "./MapVisuals.module.css";

/** Placement only: the existing tooltip content is passed through unchanged. */
export function MapHoverTooltip({ svg, objectId, revision, children }: { svg: RefObject<SVGSVGElement | null>; objectId: string; revision: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const scene = svg.current, tooltip = ref.current, canvas = scene?.parentElement;
    if (!scene || !tooltip || !canvas) return;
    const place = () => {
      const bounds = canvas.getBoundingClientRect();
      const local = (rect: DOMRect): TooltipRect => ({ left: rect.left - bounds.left - 4, right: rect.right - bounds.left + 4, top: rect.top - bounds.top - 4, bottom: rect.bottom - bounds.top + 4 });
      const obstacles: TooltipRect[] = [];
      let anchor: TooltipRect | undefined;
      for (const node of scene.querySelectorAll<SVGGElement>('[data-map-object-id]')) {
        const disc = node.querySelector<SVGCircleElement>('circle');
        if (!disc) continue;
        const rects = [disc, ...node.querySelectorAll('text, [data-metadata-badge]')].map((element) => local(element.getBoundingClientRect()));
        const orbit = node.querySelector<SVGGElement>('[data-node-orbit]');
        const matrix = orbit?.getScreenCTM?.();
        if (matrix && typeof DOMPoint !== 'undefined') {
          const center = new DOMPoint(0, 0).matrixTransform(matrix);
          const radius = Number(orbit!.getAttribute('data-orbit-extent')) * Math.max(Math.hypot(matrix.a, matrix.b), Math.hypot(matrix.c, matrix.d));
          rects.push({ left: center.x - bounds.left - radius - 4, right: center.x - bounds.left + radius + 4, top: center.y - bounds.top - radius - 4, bottom: center.y - bounds.top + radius + 4 });
        }
        obstacles.push(...rects);
        if (node.getAttribute('data-map-object-id') === objectId) {
          anchor = { left: Math.min(...rects.map((r) => r.left)), right: Math.max(...rects.map((r) => r.right)), top: Math.min(...rects.map((r) => r.top)), bottom: Math.max(...rects.map((r) => r.bottom)) };
        }
      }
      for (const element of canvas.querySelectorAll('[data-map-chrome]')) obstacles.push(local(element.getBoundingClientRect()));
      if (!anchor) return;
      const position = placeGraphTooltip(anchor, { width: tooltip.offsetWidth, height: tooltip.offsetHeight }, bounds, obstacles);
      tooltip.style.left = `${position.x}px`;
      tooltip.style.top = `${position.y}px`;
      tooltip.style.visibility = 'visible';
    };
    place();
    const frame = typeof requestAnimationFrame === 'function' ? requestAnimationFrame(place) : 0;
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(place) : null;
    observer?.observe(canvas);
    observer?.observe(tooltip);
    // React and imperative adapters can both move objects. Observe the scene's
    // geometry contract rather than requiring every caller to encode positions
    // into a React revision string. Material animation attributes are excluded.
    const geometry = typeof MutationObserver === 'function' ? new MutationObserver(place) : null;
    geometry?.observe(scene, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-pebble-x', 'data-pebble-y', 'data-pebble-radius', 'data-pebble-hot', 'data-pebble-grabbed', 'data-pebble-emphasis-scale', 'viewBox'] });
    const object = [...scene.querySelectorAll<SVGGElement>('[data-map-object-id]')].find((node) => node.getAttribute('data-map-object-id') === objectId);
    const camera = object?.closest('[data-map-camera]') ?? object?.parentElement;
    const cameraObserver = typeof MutationObserver === 'function' ? new MutationObserver(place) : null;
    if (camera) cameraObserver?.observe(camera, { attributes: true, attributeFilter: ['transform'] });
    return () => {
      if (typeof cancelAnimationFrame === 'function') cancelAnimationFrame(frame);
      observer?.disconnect(); geometry?.disconnect(); cameraObserver?.disconnect();
    };
  }, [svg, objectId, revision]);
  return <div ref={ref} className={styles.tooltip} data-graph-tooltip="" style={{ visibility: 'hidden' }} role="presentation">{children}</div>;
}
