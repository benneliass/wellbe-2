"use client";
import { useEffect, useState } from 'react';

/** Personal display preferences; never mutates the underlying health records. */
export function useGraphPins(scope: string | null) {
  const [stored, setStored] = useState<{ scope: string | null; pins: Record<string, boolean> }>({ scope: null, pins: {} });
  useEffect(() => {
    let pins: Record<string, boolean> = {};
    if (scope) try {
      const value: unknown = JSON.parse(localStorage.getItem(`wellbe.graph.pins.${scope}`) ?? '{}');
      if (value && typeof value === 'object' && !Array.isArray(value)) pins = Object.fromEntries(Object.entries(value).filter(([, pinned]) => typeof pinned === 'boolean'));
    } catch { /* Storage is optional. */ }
    setStored({ scope, pins });
  }, [scope]);
  useEffect(() => {
    if (scope && stored.scope === scope) try { localStorage.setItem(`wellbe.graph.pins.${scope}`, JSON.stringify(stored.pins)); } catch { /* Keep session preferences. */ }
  }, [scope, stored]);
  const pins = stored.scope === scope ? stored.pins : {};
  const toggle = (id: string, pinned: boolean) => setStored((previous) => {
    const next = { ...(previous.scope === scope ? previous.pins : {}), [id]: !pinned };
    return { scope, pins: next };
  });
  return { pins, toggle };
}
