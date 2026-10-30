"use client";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

export function useElementWidth<T extends HTMLElement>(): [RefObject<T | null>, number | null] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState<number | null>(null);
  // Choose the responsive scene before its first painted frame. Measuring after
  // paint briefly exposes desktop geometry inside a phone-sized map.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width || null);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => setWidth(entries[0]?.contentRect.width ?? null));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

/** Restartable UI emphasis with one owned timer and deterministic unmount cleanup. */
export function useTransientFlag(durationMs: number) {
  const [active, setActive] = useState(false);
  const timer = useRef<number | null>(null);
  const setFlag = useCallback((value = true) => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    setActive(value);
    timer.current = value ? window.setTimeout(() => { timer.current = null; setActive(false); }, durationMs) : null;
  }, [durationMs]);
  useEffect(() => () => { if (timer.current !== null) window.clearTimeout(timer.current); }, []);
  return [active, setFlag] as const;
}
