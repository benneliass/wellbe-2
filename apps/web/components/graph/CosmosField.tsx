"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { RecordGlyph, RECORD_KINDS, type RecordKind } from "./marks";
import { fitMapConstellation, growViewportLook, mapWeightDiameter, type Point, type SilkFrame, type MapCamera, resolveMapContacts, svgToGraph, arrowDelta, MAP_INTERACTION, mapObjectRadius, MAP_MOTION, subscribeMapFrame, clientToSvg, passedThreshold } from "@wellbe/ui/map/core";
import { MapObject, MapConnection, useMapEffects, useReducedMotion, useMapRoutes, useMapPan, useMapZoomBoundary } from "@wellbe/ui/map";
import styles from "./CosmosField.module.css";
import graphStyles from "./GraphLive.module.css";
import { Icon } from "@wellbe/ui";
import { graphTextWidth } from "./graphTextMetrics";

export type CosmosNode = {
  id: string;
  label: string;
  kind: RecordKind;
  degree: number;
  dim: boolean;
  pressed: boolean;
  /** Only the explicitly labeled design preview supplies reference positions. */
  referencePosition?: Point;
};
export type CosmosLink = { source: string; target: string };

type Grab = { id: string; pointerId: number; start: Point; offset: Point; moved: boolean };
const pairKey = (a: string, b: string) => JSON.stringify([a, b].sort());

/**
 * One SVG scene owns drawing and hit targets. Positions survive each walk step;
 * hover only lifts the object, and drag never becomes a navigation click.
 * SVG also keeps the actual map available without a WebGL-capable GPU.
 */
export function CosmosField({ nodes, links, path, onSelect, onClear, onSelectLink, selectedLink }: {
  nodes: CosmosNode[];
  links: CosmosLink[];
  path: readonly string[];
  onSelect: (id: string) => void;
  onClear?: () => void; onSelectLink?: (link: CosmosLink) => void; selectedLink?: CosmosLink | null;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const groups = useRef(new Map<string, SVGGElement>());
  const fullPlaces = useRef(new Map<string, Point>());
  const lookPlaces = useRef(new Map<string, Point>());
  const targets = useRef(new Map<string, Point>());
  const drawn = useRef(new Map<string, Point>());
  const grab = useRef<Grab | null>(null);
  const hovered = useRef<string | null>(null);

  const focused = useRef<string | null>(null);
  const suppressClick = useRef(false);
  const [zoom, setZoom] = useState<MapCamera>({ k: 1, tx: 0, ty: 0 });
  const [, setLayoutTick] = useState(0);
  const [home, setHome] = useState<MapCamera>({ k: 1, tx: 0, ty: 0 });
  const [homeSaved, setHomeSaved] = useState(false);
  const [hotId, setHotId] = useState<string | null>(null);
  const [grabbedId, setGrabbedId] = useState<string | null>(null);
  const reduced = useReducedMotion();
  const repaint = useRef<() => void>(() => {});
  const [size, setSize] = useState({ width: 1100, height: 620 });
  const latest = useRef({ nodes, links, path });
  latest.current = { nodes, links, path };
  const topology = JSON.stringify([nodes.map((node) => [node.id, node.degree]), links]);
  const route = JSON.stringify(path);
  const pan = useMapPan({ camera: zoom, viewport: size, onChange: setZoom, onBackgroundClick: () => onClear?.() });
  useMapZoomBoundary(svg, zoomAt, () => setZoom(home), () => { pan.cancel(); grab.current = null; setGrabbedId(null); suppressClick.current = true; });
  function zoomAt(factor: number, cx: number, cy: number) {
    const scene = svg.current;
    if (!scene || !Number.isFinite(factor) || factor <= 0) return;
    const point = clientToSvg(scene, cx, cy, size);
    setZoom((before) => {
      const k = Math.min(MAP_INTERACTION.maxZoom, Math.max(MAP_INTERACTION.minZoom, before.k * factor));
      const ratio = k / before.k;
      return { k, tx: point.x - (point.x - before.tx) * ratio, ty: point.y - (point.y - before.ty) * ratio };
    });
  }

  useLayoutEffect(() => {
    const element = stage.current;
    if (!element) return;
    const measure = () => {
      const width = element.clientWidth || 1100;
      const height = element.clientHeight || 620;
      setSize((before) => before.width === width && before.height === height ? before : { width, height });
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    const { nodes: records, links: associations } = latest.current;
    const fitted = fitMapConstellation(records, associations, size.width, size.height);
    const mobile = size.width < 600;
    records.forEach((node, index) => {
      if (!node.referencePosition) return;
      // The same sample constellation becomes a readable vertical map on a phone.
      fitted.set(node.id, mobile ? {
        x: size.width * (0.23 + (index % 2) * 0.52),
        y: 55 + Math.floor(index / 2) * (size.height - 110) / Math.max(1, Math.ceil(records.length / 2) - 1),
      } : { x: node.referencePosition.x * size.width, y: node.referencePosition.y * size.height });
    });
    fullPlaces.current = fitted;
    lookPlaces.current.clear();
    targets.current = new Map(fitted);
    drawn.current = new Map(fitted);
    setLayoutTick((tick) => tick + 1);
    setZoom({ k: 1, tx: 0, ty: 0 });
    setHome({ k: 1, tx: 0, ty: 0 }); setHomeSaved(false);
    // A resize may happen while looking at a record; the route effect below
    // re-seats its neighborhood using the new viewport.
  }, [topology, size.width, size.height]);

  useLayoutEffect(() => {
    const { nodes: records, links: associations, path: walk } = latest.current;
    const tip = walk.at(-1);
    if (!tip) {
      lookPlaces.current.clear();
      targets.current = new Map(fullPlaces.current);
      setLayoutTick((tick) => tick + 1);
      return;
    }
    const shown = new Set(walk);
    for (const link of associations) {
      if (link.source === tip) shown.add(link.target);
      if (link.target === tip) shown.add(link.source);
    }
    const radius = (degree: number) => mapWeightDiameter(degree) * (size.width < 600 ? 0.86 : 1.28);
    if (!lookPlaces.current.has(tip)) {
      const kept = drawn.current.get(tip) ?? targets.current.get(tip) ?? fullPlaces.current.get(tip);
      if (kept) lookPlaces.current.set(tip, { ...kept });
    }
    const next = growViewportLook({
      stored: lookPlaces.current,
      background: targets.current,
      shownIds: [...new Set([...lookPlaces.current.keys(), ...shown])],
      latestId: tip,
      radii: new Map(records.map((node) => [node.id, radius(node.degree)])),
      labelWidths: new Map(records.map((node) => [node.id, Math.min(node.label.length * (size.width < 600 ? 7 : 9), 168)])),
      width: size.width,
      height: size.height,
    });
    lookPlaces.current = next;
    targets.current = new Map([...fullPlaces.current, ...next]);
    setLayoutTick((tick) => tick + 1);
  }, [route, topology, size.width, size.height]);

  const routingPoint = (node: CosmosNode) => ({ ...(targets.current.get(node.id) ?? { x: 0, y: 0 }), r: mapObjectRadius(node.degree), labelWidth: graphTextWidth(node.label, 12.5, 450) + 8, labelTop: mapObjectRadius(node.degree) + 1, labelBottom: mapObjectRadius(node.degree) + 24, allowUnderLabel: true });
  const routed = useMapRoutes(targets.current.size ? links.map((link) => ({ id: pairKey(link.source, link.target), a: routingPoint(nodes.find((node) => node.id === link.source)!), b: routingPoint(nodes.find((node) => node.id === link.target)!), obstacles: nodes.filter((node) => node.id !== link.source && node.id !== link.target).map(routingPoint) })) : [], size, grabbedId !== null);
  const routes = new Map(routed.map((edge) => [edge.id, edge]));
  // This map owns placement and walk policy; the shared toolkit owns all material motion.
  useLayoutEffect(() => {
    let previous = 0;
    const paint = (now: number) => {
      const ease = reduced ? 1 : 1 - Math.exp(-Math.min(now - previous || 16, 64) / MAP_MOTION.positionSettleMs);
      previous = now;
      for (const node of latest.current.nodes) {
        const home = targets.current.get(node.id), group = groups.current.get(node.id);
        if (!home || !group) continue;
        const before = drawn.current.get(node.id) ?? home;
        const point = grab.current?.id === node.id ? home : { x: before.x + (home.x - before.x) * ease, y: before.y + (home.y - before.y) * ease };
        drawn.current.set(node.id, point);
        group.setAttribute('transform', `translate(${point.x} ${point.y})`);
        const object = group.querySelector('[data-map-object-id]');
        object?.setAttribute('data-pebble-x', String(point.x));
        object?.setAttribute('data-pebble-y', String(point.y));
      }

    };
    repaint.current = () => paint(performance.now());
    paint(performance.now());
    svg.current?.removeAttribute('data-ready');
    const readyFrame = requestAnimationFrame(() => { paint(performance.now()); svg.current?.setAttribute('data-ready', 'true'); });
    const unsubscribe = !reduced && svg.current ? subscribeMapFrame(svg.current, paint, -20) : () => {};
    return () => { cancelAnimationFrame(readyFrame); unsubscribe(); repaint.current = () => {}; };
  }, [topology, route, size.width, size.height, reduced]);
  useMapEffects(svg, reduced, `${topology}|${size.width}x${size.height}`);

  function connectionFrame(link: CosmosLink): SilkFrame {
    const points = new Map(latest.current.nodes.map((node) => {
      const point = drawn.current.get(node.id) ?? targets.current.get(node.id) ?? { x: 0, y: 0 };
      const scale = Number(groups.current.get(node.id)?.querySelector('[data-pebble-object]')?.getAttribute('data-pebble-scale') ?? 1);
      return [node.id, { ...point, r: mapObjectRadius(node.degree) * scale, allowUnderLabel: true }];
    }));
    const base = (id: string) => ({ ...points.get(id)!, r: mapObjectRadius(latest.current.nodes.find((node) => node.id === id)!.degree) });
    const planned = routes.get(pairKey(link.source, link.target));
    return { preferredRoute: planned?.route ? { d: planned.route.d, a: planned.a, b: planned.b } : undefined, peerRoutes: routed.flatMap((edge) => edge.id !== planned?.id && edge.route ? [edge.route.points] : []), a: base(link.source), b: base(link.target), obstacles: [...points].filter(([id]) => id !== link.source && id !== link.target).map(([, point]) => point), viewport: size,
      revision: `${topology}|${size.width}x${size.height}`, calm: reduced, interacting: grab.current !== null,
      hot: hovered.current === link.source || hovered.current === link.target };
  }

  function pointerPosition(event: React.PointerEvent<SVGGElement>): Point {
    return svg.current ? svgToGraph(clientToSvg(svg.current, event.clientX, event.clientY, size), zoom) : { x: 0, y: 0 };
  }
  function release(event: React.PointerEvent<SVGGElement>, cancelled = false) {
    if (grab.current?.pointerId !== event.pointerId) return;
    if (grab.current.moved || cancelled) suppressClick.current = true;
    grab.current = null; setGrabbedId(null); setLayoutTick((tick) => tick + 1);
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    repaint.current();
  }
  function moveRecord(id: string, point: Point) {
    const boxes = latest.current.nodes.map((node) => {
      const p = node.id === id ? point : targets.current.get(node.id) ?? { x: 0, y: 0 };
      const r = mapObjectRadius(node.degree), growth = r * (MAP_MOTION.selectedScale - 1) + 4;
      return { id: node.id, ...p, hw: Math.max(r + growth, graphTextWidth(node.label, 12.5, 450) * 1.06 / 2 + 4), up: r + growth + 6, down: r + 26 };
    });
    const contacts = resolveMapContacts(boxes, { active: new Set([id]), fixed: new Set([id]), origins: Object.fromEntries(targets.current), left: 12, top: 12 });
    for (const node of latest.current.nodes) {
      const next = contacts[node.id]!;
      targets.current.set(node.id, next);
      fullPlaces.current.set(node.id, next);
      if (path.length && (lookPlaces.current.has(node.id) || node.id === id)) lookPlaces.current.set(node.id, next);
    }
    repaint.current();
  }
  return <div className={styles.stage} ref={stage}>
    <svg ref={svg} className={styles.scene} viewBox={`0 0 ${size.width} ${size.height}`} aria-label="Your records context map" style={{ cursor: grabbedId || pan.gesture.current ? 'grabbing' : 'grab', touchAction: 'none' }}
      onPointerDown={pan.onPointerDown} onPointerMove={pan.onPointerMove} onPointerUp={pan.onPointerUp} onPointerLeave={pan.onPointerLeave} onPointerCancel={pan.onPointerCancel}
      onKeyDown={(event) => { if (event.key === 'Escape') onClear?.(); }}>
      <g data-map-camera="" transform={`translate(${zoom.tx} ${zoom.ty}) scale(${zoom.k})`}>
      <g aria-hidden="true" className={styles.links}>
        {links.map((link) => {
          const currentStep = path.length > 1 && pairKey(link.source, link.target) === pairKey(path.at(-2)!, path.at(-1)!);
          const chosen = selectedLink && pairKey(selectedLink.source, selectedLink.target) === pairKey(link.source, link.target);
          const touched = path.includes(link.source) || path.includes(link.target);
          const frame = connectionFrame(link);
          return <MapConnection key={pairKey(link.source, link.target)} id={pairKey(link.source, link.target)} source={link.source} target={link.target}
            {...frame} getFrame={() => connectionFrame(link)}
            stroke={RECORD_KINDS[nodes.find((node) => node.id === link.source)!.kind].color} endStroke={RECORD_KINDS[nodes.find((node) => node.id === link.target)!.kind].color}
            width={1.35} opacity={0.72}
            faded={path.length > 0 && !touched && !chosen} active={Boolean(chosen || currentStep || hotId === link.source || hotId === link.target || path.at(-1) === link.source || path.at(-1) === link.target)} flow={Boolean((currentStep || chosen) && !reduced)} onSelect={onSelectLink ? () => onSelectLink(link) : undefined} />;
        })}
      </g>
      {nodes.map((node) => {
        const r = mapObjectRadius(node.degree);
        return <g key={node.id} ref={(element) => { if (element) groups.current.set(node.id, element); else groups.current.delete(node.id); }}
          data-record-id={node.id} data-dim={node.dim} data-current={node.pressed} data-hot={hotId === node.id || grabbedId === node.id}>
          <MapObject objectId={node.id} data-object="" position={{ x: 0, y: 0 }} radius={r} hitRadius={22} accessibleLabel={node.label}
            appearance={{ color: RECORD_KINDS[node.kind].color, shape: 'pebble', opacity: 1 }}
            glyph={<svg viewBox="0 0 24 24" width="13" height="13"><RecordGlyph kind={node.kind} /></svg>}
            label={{ text: node.label, offset: 16 }} state={{ selected: node.pressed, hot: hotId === node.id, grabbed: grabbedId === node.id, opacity: node.dim ? 0.3 : 1 }}
            onPointerEnter={() => { hovered.current = node.id; setHotId(node.id); }}
            onPointerLeave={() => { hovered.current = null; if (focused.current !== node.id) setHotId(null); }}
            onFocus={() => { focused.current = node.id; setHotId(node.id); }}
            onBlur={() => { focused.current = null; if (hovered.current !== node.id) setHotId(null); }}
            onPointerDown={(event) => {
              if (event.button !== 0) return;
              const point = pointerPosition(event), center = drawn.current.get(node.id) ?? point;
              suppressClick.current = false;
              grab.current = { id: node.id, pointerId: event.pointerId, start: { x: event.clientX, y: event.clientY }, offset: { x: center.x - point.x, y: center.y - point.y }, moved: false };
              setGrabbedId(node.id); event.currentTarget.setPointerCapture?.(event.pointerId);
            }}
            onPointerMove={(event) => {
              const held = grab.current;
              if (!held || held.pointerId !== event.pointerId) return;
              if (!held.moved && !passedThreshold(event.clientX - held.start.x, event.clientY - held.start.y)) return;
              held.moved = true; suppressClick.current = true;
              const pointer = pointerPosition(event);
              const margin = r * MAP_MOTION.selectedScale + 12;
              const point = { x: Math.max(margin, Math.min(size.width - margin, pointer.x + held.offset.x)), y: Math.max(margin, Math.min(size.height - margin - 32, pointer.y + held.offset.y)) };
              moveRecord(node.id, point);
            }}
            onPointerUp={(event) => release(event)} onPointerCancel={(event) => release(event, true)}
            onLostPointerCapture={() => { grab.current = null; setGrabbedId(null); }}
            onClick={() => { if (!suppressClick.current) onSelect(node.id); }}
            onKeyDown={(event) => {
              const delta = arrowDelta(event.key, event.shiftKey);
              if (delta && !event.altKey) { event.preventDefault(); event.stopPropagation(); const p = targets.current.get(node.id)!; moveRecord(node.id, { x: p.x + delta.x, y: p.y + delta.y }); setLayoutTick((tick) => tick + 1); }
              else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(node.id); }
            }} />
        </g>;
      })}
      </g>
    </svg>
    <div className={graphStyles.zoomControls} data-map-chrome="">
      <button type="button" className={graphStyles.zoomBtn} aria-label="Zoom in" onClick={() => { const rect = svg.current!.getBoundingClientRect(); zoomAt(1.2, rect.x + rect.width / 2, rect.y + rect.height / 2); }}><Icon name="plus" size={15} /></button>
      <button type="button" className={graphStyles.zoomBtn} aria-label="Zoom out" onClick={() => { const rect = svg.current!.getBoundingClientRect(); zoomAt(1 / 1.2, rect.x + rect.width / 2, rect.y + rect.height / 2); }}><Icon name="chevron-down" size={15} /></button>
      <button type="button" className={graphStyles.zoomBtn} aria-label="Recenter map" onClick={() => setZoom(home)}><Icon name="home" size={15} /></button>
      <button type="button" className={graphStyles.zoomBtn} aria-label="Set current view as default" aria-pressed={homeSaved} onClick={() => { setHome(zoom); setHomeSaved(true); }}><Icon name={homeSaved ? 'check' : 'star'} size={15} /></button>
    </div>
  </div>;
}
