import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MapObject, MapOrbit, MapSurface, mapObjectHandlers, useMapZoomBoundary } from '@wellbe/ui/map';
import { MAP_MOTION, MapFrameClock, graphOrbitExtent, graphOrbitSlots, pebbleBreathAmplitude, pebblePalette, porcelainTint } from '@wellbe/ui/map/core';
import { useRef } from 'react';

describe('portable map toolkit contracts', () => {
  it('renders unrelated domains and different characteristics through the same object API', () => {
    const activate = vi.fn(), context = vi.fn(), navigate = vi.fn(), nudge = vi.fn();
    const { container } = render(<svg>
      <MapObject objectId="stream-7" accessibleLabel="Ingestion stream" position={{ x: 120, y: 80 }} radius={24}
        appearance={{ color: '#8056ad', shape: 'diamond' }} glyph={<svg viewBox="0 0 24 24"><path d="M0 0L24 24" /></svg>}
        label={{ text: 'Ingestion stream', offset: 30, secondary: { text: 'Queued', color: '#8056ad' } }}
        state={{ selected: true }} {...mapObjectHandlers({ activate, context, navigate, nudge })} />
      <MapObject objectId="document-2" accessibleLabel="Stored document" position={{ x: 260, y: 80 }} radius={18}
        appearance={{ color: '#287d80', shape: 'pebble', opacity: 0.65 }} glyph={<svg />} label={{ text: 'Stored document' }} />
    </svg>);
    const object = screen.getByRole('button', { name: 'Ingestion stream' });
    fireEvent.click(object);
    fireEvent.keyDown(object, { key: 'Enter' });
    fireEvent.keyDown(object, { key: ' ', code: 'Space' });
    fireEvent.keyDown(object, { key: 'F10', shiftKey: true });
    fireEvent.keyDown(object, { key: 'ArrowRight', altKey: true });
    fireEvent.keyDown(object, { key: 'ArrowDown', shiftKey: true });
    expect(activate).toHaveBeenCalledTimes(3);
    expect(context).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledWith('ArrowRight');
    expect(nudge).toHaveBeenCalledWith('ArrowDown', true);
    expect(object).toHaveAttribute('aria-pressed', 'true');
    expect(container.querySelector('[data-map-object-id="document-2"] [data-map-surface]')).toHaveAttribute('opacity', '0.65');
    const labels = [...object.querySelectorAll('text')];
    expect(Number(labels[1]!.getAttribute('y'))).toBeGreaterThan(Number(labels[0]!.getAttribute('y')));
  });

  it('shares orbital envelopes and stable local paint ids across independent objects', () => {
    const items = Array.from({ length: 8 }, (_, i) => ({ id: `item-${i}`, label: `Item ${i}`, kind: 'generic-record', color: '#6984bf', glyph: <svg viewBox="0 0 24 24" /> }));
    const { container } = render(<svg><MapOrbit items={items} radius={22} /><MapSurface radius={30} appearance={{ color: '#8056ad' }} /><MapSurface radius={30} appearance={{ color: '#8056ad' }} /></svg>);
    expect(container.querySelectorAll('[data-orbit-item]')).toHaveLength(8);
    const slots = graphOrbitSlots(22, items.length);
    const envelope = graphOrbitExtent(22, items.length);
    expect(new Set(slots.map((slot) => slot.distance)).size).toBe(2);
    for (const slot of slots) expect(slot.distance + slot.itemRadius).toBeLessThan(envelope);
    const ids = [...container.querySelectorAll('[id]')].map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('keeps the physical shader deterministic and the motion profile configurable', () => {
    expect(pebblePalette('#369')).toEqual(pebblePalette('#336699'));
    expect(porcelainTint('#369', 0.3)).toBe(porcelainTint('#336699', 0.3));
    expect(() => pebblePalette('not-a-color')).toThrow('hex');
    expect(pebbleBreathAmplitude(40)).toBe(0.04);
    expect(pebbleBreathAmplitude(40, { ...MAP_MOTION, breathTravelPx: 2, minBreathScale: 0.01, maxBreathScale: 0.1 })).toBe(0.05);
  });

  it('keeps default labels below custom miniature sizes and multiple rings', () => {
    const config = { itemRadius: 12, gap: 6, itemsPerRing: 3, maxItems: 9 };
    const items = Array.from({ length: 7 }, (_, i) => ({ id: String(i), label: `Item ${i}`, color: '#6984bf', glyph: <svg /> }));
    const { container } = render(<svg><MapObject objectId="large-orbit" accessibleLabel="Large orbit" position={{ x: 100, y: 100 }} radius={30}
      appearance={{ color: '#6984bf' }} glyph={<svg />} orbitItems={items} orbitConfig={config} label={{ text: 'Kept clear', offset: undefined }} /></svg>);
    const baseline = Number(container.querySelector('text')!.getAttribute('y'));
    expect(baseline).toBeGreaterThanOrEqual(100 + graphOrbitExtent(30, items.length, config) + 12);
  });

  it('runs objects and links on one cancellable clock and isolates a broken listener', () => {
    let next = 0;
    const pending = new Map<number, FrameRequestCallback>();
    const cancel = vi.fn((id: number) => pending.delete(id));
    const errors: unknown[] = [], calls: string[] = [];
    const clock = new MapFrameClock({ request: (paint) => { const id = ++next; pending.set(id, paint); return id; }, cancel }, (error) => errors.push(error));
    const offObjects = clock.subscribe(() => calls.push('objects'));
    const offLinks = clock.subscribe(() => calls.push('links'), -10);
    const offBroken = clock.subscribe(() => { throw new Error('custom painter'); }, -5);
    expect(pending.size).toBe(1);
    const [id, paint] = [...pending][0]!;
    pending.delete(id);
    paint(100);
    expect(calls).toEqual(['links', 'objects']);
    expect(errors).toHaveLength(1);
    expect(pending.size).toBe(1);
    offLinks(); offObjects(); offBroken();
    expect(pending.size).toBe(0);
    expect(cancel).toHaveBeenCalledTimes(1);
  });

  it('directs keyboard zoom to the focused map when another map is under the pointer', () => {
    const first = vi.fn(), second = vi.fn();
    function Surface({ name, onZoom, left }: { name: string; onZoom: () => void; left: number }) {
      const ref = useRef<SVGSVGElement>(null);
      useMapZoomBoundary(ref, onZoom, () => {}, () => {});
      return <div ref={(element) => { if (element) element.getBoundingClientRect = () => ({ x: left, y: 0, left, top: 0, right: left + 100, bottom: 100, width: 100, height: 100, toJSON: () => ({}) }); }}><svg ref={ref}><g tabIndex={0} role="button" aria-label={name} /></svg></div>;
    }
    render(<><Surface name="First map" onZoom={first} left={0} /><Surface name="Second map" onZoom={second} left={200} /></>);
    const focused = screen.getByRole('button', { name: 'First map' });
    focused.focus();
    fireEvent.pointerMove(document, { clientX: 250, clientY: 50 });
    fireEvent.keyDown(document, { key: '+', ctrlKey: true });
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).not.toHaveBeenCalled();
  });
});
