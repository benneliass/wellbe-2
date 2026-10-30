"use client";
import { useRef, type PointerEvent } from 'react';
import type { MapCamera } from './core/types';

/** Shared background click/pan policy. Snapshot coordinates before queued updates
 * so release, cancellation or pinch cannot invalidate a pending camera update. */
export function useMapPan({ camera, viewport, onChange, onBackgroundClick }: {
  camera: MapCamera; viewport: { width: number; height: number };
  onChange: (update: (previous: MapCamera) => MapCamera) => void; onBackgroundClick: () => void;
}) {
  const pan = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);
  const cancel = () => { pan.current = null; };
  return {
    cancel,
    gesture: pan,
    onPointerDown(event: PointerEvent<SVGSVGElement>) {
      if (event.button > 0 || (event.target as Element).closest('[data-map-object-id], [data-silk-link], [data-drag], [data-map-chrome]')) return;
      pan.current = { x: event.clientX, y: event.clientY, tx: camera.tx, ty: camera.ty, moved: false };
    },
    onPointerMove(event: PointerEvent<SVGSVGElement>) {
      const held = pan.current, rect = event.currentTarget.getBoundingClientRect();
      if (!held || rect.width <= 0 || rect.height <= 0) return;
      const dx = (event.clientX - held.x) / rect.width * viewport.width, dy = (event.clientY - held.y) / rect.height * viewport.height;
      if (Math.abs(dx) + Math.abs(dy) > 2) held.moved = true;
      const tx = held.tx + dx, ty = held.ty + dy;
      onChange((previous) => ({ ...previous, tx, ty }));
    },
    onPointerUp() {
      const held = pan.current; pan.current = null;
      if (held && !held.moved) onBackgroundClick();
    },
    onPointerLeave: cancel,
    onPointerCancel: cancel,
  };
}
