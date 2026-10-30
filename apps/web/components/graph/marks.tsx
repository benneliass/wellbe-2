import { LivingPebbleSurface } from "@wellbe/ui/map";
import type { BridgeBearing } from "@wellbe/ui/map/core";

import { RECORD_KINDS, type RecordKind } from "./recordKinds";
export { RECORD_KINDS, type RecordKind } from "./recordKinds";

export { porcelainTint } from "@wellbe/ui/map/core";

/** Optical proportions follow the reference; filled bars and heavier bevels stay clear at small sizes. */
export function RecordGlyph({ kind }: { kind: RecordKind }) {
  return <g fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round">
    {kind === "note" && <><rect x="4.7" y="2.8" width="14.6" height="18.4" rx="2.1" /><path d="M8.4 7.5h7.2M8.4 12h7.2M8.4 16.5h5.1" /></>}
    {kind === "document" && <><path d="M5.6 2.8h8.7l4.5 4.7v13.7H5.6z" /><path d="M14.3 2.8v5h4.5" /></>}
    {kind === "result" && <g fill="currentColor" stroke="none"><rect x="4" y="13" width="3.6" height="8.2" rx="1.3" /><rect x="10.2" y="2.8" width="3.6" height="18.4" rx="1.3" /><rect x="16.4" y="8" width="3.6" height="13.2" rx="1.3" /></g>}
    {kind === "other" && <><rect x="9" y="2.8" width="6" height="12.3" rx="3" /><path d="M6 10.9v1.4a6 6 0 0012 0v-1.4M12 18.3v3.5M9 21.8h6" /></>}
    {kind === "hub" && <>{[3.8, 13.6].flatMap((x) => [3.8, 13.6].map((y) => <rect key={`${x}-${y}`} x={x} y={y} width="6.6" height="6.6" rx="1.6" />))}</>}
  </g>;
}

/** The filled circle both maps use. Size and color come from the caller. */
export function RecordCircle({
  x,
  y,
  r,
  opacity = 1,
  color = "#0ea5a4",
  segments,
  segmentBearings,
}: {
  x: number;
  y: number;
  r: number;
  opacity?: number;
  color?: string;
  segments?: readonly string[];
  segmentBearings?: readonly BridgeBearing[];
}) {
  return (
    <g transform={`translate(${x} ${y})`} opacity={opacity}>
      <LivingPebbleSurface radius={r} color={color} segments={segments} segmentBearings={segmentBearings} />
    </g>
  );
}
