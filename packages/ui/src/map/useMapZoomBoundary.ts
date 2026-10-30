"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

type ZoomAt = (factor: number, clientX: number, clientY: number) => void;

/** Own browser zoom gestures while this map is mounted; ordinary page scrolling still works. */
export function useMapZoomBoundary(svg: RefObject<SVGSVGElement | null>, zoomAt: ZoomAt, reset: () => void, beginPinch: () => void) {
  const callbacks = useRef({ zoomAt, reset, beginPinch });
  callbacks.current = { zoomAt, reset, beginPinch };
  useLayoutEffect(() => {
    let inside = false;
    let touch: { distance: number; inside: boolean } | null = null;
    let gestureScale = 1;
    const canvas = () => svg.current?.parentElement;
    const active = () => Boolean(svg.current && !svg.current.closest('[inert], [aria-hidden="true"]'));
    const contains = (target: EventTarget | null) => active() && target instanceof Node && Boolean(canvas()?.contains(target));
    const overMap = (x: number, y: number) => {
      if (!active()) return false;
      const box = canvas()?.getBoundingClientRect();
      return Boolean(box && x >= box.left && x <= box.right && y >= box.top && y <= box.bottom);
    };
    const move = (event: PointerEvent) => { inside = overMap(event.clientX, event.clientY); };
    const wheel = (event: WheelEvent) => {
      if (!active()) return;
      const map = contains(event.target);
      if (!map && !event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      if (!map) return;
      event.stopPropagation();
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 240 : 1);
      callbacks.current.zoomAt(Math.exp(-Math.max(-150, Math.min(150, delta)) * (event.ctrlKey ? 0.009 : 0.0025)), event.clientX, event.clientY);
    };
    const keyboard = (event: KeyboardEvent) => {
      if (!active()) return;
      if (!(event.ctrlKey || event.metaKey) || !['+', '=', '-', '_', '0'].includes(event.key)) return;
      event.preventDefault();
      const focusedMap = document.activeElement?.closest('[data-map-zoom-ready]');
      if (focusedMap ? !contains(document.activeElement) : !inside) return;
      const box = canvas()?.getBoundingClientRect();
      if (!box) return;
      if (event.key === '0') callbacks.current.reset();
      else callbacks.current.zoomAt(event.key === '-' || event.key === '_' ? 1 / 1.2 : 1.2, box.x + box.width / 2, box.y + box.height / 2);
    };
    const touchStart = (event: TouchEvent) => {
      if (!active()) return;
      if (event.touches.length !== 2) return;
      event.preventDefault();
      const a = event.touches[0]!, b = event.touches[1]!;
      touch = { distance: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), inside: contains(event.target) };
      if (touch.inside) { event.stopPropagation(); callbacks.current.beginPinch(); }
    };
    const touchMove = (event: TouchEvent) => {
      if (!active()) return;
      if (event.touches.length !== 2) return;
      event.preventDefault();
      const a = event.touches[0]!, b = event.touches[1]!;
      const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (touch?.inside) {
        event.stopPropagation();
        callbacks.current.zoomAt(distance / Math.max(1, touch.distance), (a.clientX + b.clientX) / 2, (a.clientY + b.clientY) / 2);
      }
      if (touch) touch.distance = distance;
    };
    const touchEnd = () => { touch = null; };
    // Safari supplies gesture events; Chromium trackpads supply ctrl+wheel.
    const gesture = (event: Event) => {
      if (!active()) return;
      event.preventDefault();
      if (touch || !contains(event.target)) return;
      const value = event as Event & { scale?: number; clientX?: number; clientY?: number };
      if (event.type === 'gesturestart') { gestureScale = 1; callbacks.current.beginPinch(); }
      else if (event.type === 'gesturechange') {
        const box = canvas()?.getBoundingClientRect();
        if (!box) return;
        const scale = value.scale ?? 1;
        callbacks.current.zoomAt(scale / gestureScale, value.clientX ?? box.x + box.width / 2, value.clientY ?? box.y + box.height / 2);
        gestureScale = scale;
      }
    };
    const options = { capture: true, passive: false };
    document.addEventListener('pointermove', move, true);
    document.addEventListener('wheel', wheel, options);
    document.addEventListener('keydown', keyboard, true);
    document.addEventListener('touchstart', touchStart, options);
    document.addEventListener('touchmove', touchMove, options);
    document.addEventListener('touchend', touchEnd, true);
    document.addEventListener('touchcancel', touchEnd, true);
    for (const name of ['gesturestart', 'gesturechange', 'gestureend']) document.addEventListener(name, gesture, options);
    svg.current?.setAttribute('data-map-zoom-ready', 'true');
    return () => {
      svg.current?.removeAttribute('data-map-zoom-ready');
      document.removeEventListener('pointermove', move, true);
      document.removeEventListener('wheel', wheel, true);
      document.removeEventListener('keydown', keyboard, true);
      document.removeEventListener('touchstart', touchStart, true);
      document.removeEventListener('touchmove', touchMove, true);
      document.removeEventListener('touchend', touchEnd, true);
      document.removeEventListener('touchcancel', touchEnd, true);
      for (const name of ['gesturestart', 'gesturechange', 'gestureend']) document.removeEventListener(name, gesture, true);
    };
  }, [svg]);
}
