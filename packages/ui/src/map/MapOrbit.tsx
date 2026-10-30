import type { MapMiniatureItem } from './visualTypes';
import { GRAPH_ORBIT, graphOrbitExtent, graphOrbitSlots, type GraphOrbitConfig } from './core/orbit';
import { MapMiniature } from './MapMiniature';
import styles from './MapVisuals.module.css';

export function MapOrbit({ items, radius, config = GRAPH_ORBIT }: { items: readonly MapMiniatureItem[]; radius: number; config?: Readonly<GraphOrbitConfig> }) {
  const slots = graphOrbitSlots(radius, items.length, config);
  if (!slots.length) return null;
  return <g data-node-orbit="" data-orbit-extent={graphOrbitExtent(radius, items.length, config)} data-orbit-base-extent={graphOrbitExtent(radius, items.length, config)} className={styles.orbit}>
    {slots.map((slot, index) => {
      const item = items[index]!;
      return <g key={item.id} data-orbit-dot={slot.angle} data-orbit-kind={item.kind} data-orbit-item={item.id} data-orbit-x={slot.x} data-orbit-y={slot.y} data-orbit-radius={slot.distance} data-orbit-base-radius={slot.distance} data-orbit-item-radius={slot.itemRadius} className={styles.orbitDot} transform={`translate(${slot.x} ${slot.y})`}><MapMiniature item={item} radius={slot.itemRadius} /></g>;
    })}
  </g>;
}
