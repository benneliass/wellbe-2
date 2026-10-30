import { MapShapeGeometry } from './MapShapeGeometry';
import type { MapShape } from './visualTypes';
import styles from './MapVisuals.module.css';

/** A traveling reflection on the material's own edge, never an outer ring.
 * Selection starts it; dragging pauses it and reduced motion keeps a still glint.
 */
export function MapEdgeFlow({ radius, shape }: { radius: number; shape: MapShape }) {
  return <g data-map-edge-flow="" className={styles.edgeFlow} aria-hidden="true" pointerEvents="none">
    <MapShapeGeometry radius={radius} shape={shape} className={`${styles.edgeFlowTrace} ${styles.edgeFlowGlow}`} fill="none" pathLength={100} strokeDasharray="22 78" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    <MapShapeGeometry radius={radius} shape={shape} className={`${styles.edgeFlowTrace} ${styles.edgeFlowCore}`} fill="none" pathLength={100} strokeDasharray="14 86" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
  </g>;
}
