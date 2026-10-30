import type { ReactNode } from 'react';
import { bridgeArcPaths, type BridgeBearing } from './core/segments';
import type { MapAccentProfile } from './visualTypes';
import styles from './MapVisuals.module.css';

export function MapAccents({ x = 0, y = 0, radius: r, color, profile, segments, bearings, children }: {
  x?: number; y?: number; radius: number; color: string; profile: MapAccentProfile;
  segments?: readonly string[]; bearings?: readonly BridgeBearing[]; children?: ReactNode;
}) {
  const { kind, dash, period } = profile;
  return <g transform={`translate(${x} ${y})`} data-node-accents={profile.name ?? kind} data-accent-type={profile.type} data-accent-period={period} aria-hidden="true" pointerEvents="none" color={color}>
    <g data-accent-envelope="">{kind === 'none' ? null : kind === 'diamond' ? <g transform="rotate(45)"><rect data-accent-sheen="" className={styles.accentTrace} x={-r + 2} y={-r + 2} width={(r - 2) * 2} height={(r - 2) * 2} rx="5" pathLength="100" strokeDasharray={dash} /></g>
      : kind === 'bridge' ? segments?.map((segment, index) => <path key={index} data-bridge-accent={index} className={styles.accentTrace} style={{ color: segment }} d={bridgeArcPaths(segments.length, r + 4, bearings)[index]} />)
      : kind === 'external' ? <g transform="rotate(-28)"><ellipse data-accent-sheen="" className={styles.accentTrace} rx={r + 5} ry={r + 1} pathLength="100" strokeDasharray={dash} /></g>
      : kind === 'open-loop' || kind === 'comparison' ? <circle data-accent-sheen="" className={styles.accentTrace} r={r + 4} pathLength="100" strokeDasharray={kind === 'comparison' ? '1 9' : '4 8'} />
      : <g data-accent-rotate="1"><circle className={styles.accentTrace} r={r + 4} pathLength="100" strokeDasharray={dash} />{(kind === 'layered' || kind === 'paired') && <circle className={styles.accentTrace} r={r + 2} pathLength="100" strokeDasharray={dash} strokeDashoffset="-45" />}</g>}</g>
    {children}
  </g>;
}
