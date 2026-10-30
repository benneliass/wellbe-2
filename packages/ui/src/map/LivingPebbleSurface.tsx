"use client";

import { useId } from "react";
import { PEBBLE_OUTLINE, pebblePalette, bridgeFillPaths, type BridgeBearing } from "./core";
import { MapShapeGeometry } from './MapShapeGeometry';
import { MapEdgeFlow } from './MapEdgeFlow';

/** Shared, scalable material: sculpted silhouette, soft glaze and fine ceramic grain. */
export function LivingPebbleSurface({ radius, color, segments, segmentBearings }: { radius: number; color: string; segments?: readonly string[]; segmentBearings?: readonly BridgeBearing[] }) {
  const id = `pebble-${useId().replace(/:/g, "")}`;
  const paint = pebblePalette(color);
  const segmentPaths = segments ? bridgeFillPaths(segments.length, segmentBearings) : [];
  return <g data-porcelain-surface="" data-pebble-material="living-pebble" data-radius={radius}>
    <defs>
      <radialGradient id={`${id}-body`} data-pebble-light="" cx="28%" cy="18%" r="65%" fx="25%" fy="15%">
        <stop offset="0" stopColor={paint.light} />
        <stop offset="0.28" stopColor={paint.crown} />
        <stop offset="0.64" stopColor={paint.body} />
        <stop offset="0.88" stopColor={paint.base} />
        <stop offset="1" stopColor={paint.base} />
      </radialGradient>
      {segments?.map((segment, index) => {
        const p = pebblePalette(segment);
        return <radialGradient id={`${id}-segment-${index}`} key={index} cx="28%" cy="18%" r="65%" fx="25%" fy="15%">
          <stop stopColor={p.light} /><stop offset="0.28" stopColor={p.crown} /><stop offset="0.64" stopColor={p.body} /><stop offset="0.88" stopColor={p.base} /><stop offset="1" stopColor={p.base} />
        </radialGradient>;
      })}
      <radialGradient id={`${id}-crown`} cx="32%" cy="14%" r="60%">
        <stop stopColor="#fff" stopOpacity="0.72" />
        <stop offset="0.48" stopColor="#fff" stopOpacity="0.13" />
        <stop offset="1" stopColor="#fff" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-window`} cx="18%" cy="40%" r="56%">
        <stop stopColor="#fff" stopOpacity="0.45" />
        <stop offset="0.48" stopColor="#fff" stopOpacity="0.2" />
        <stop offset="1" stopColor="#fff" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-shade`} cx="75%" cy="85%" r="65%">
        <stop stopColor="#263e52" stopOpacity="0.08" />
        <stop offset="0.65" stopColor="#263e52" stopOpacity="0.02" />
        <stop offset="1" stopColor="#263e52" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-glint`}>
        <stop stopColor="#fff" stopOpacity="0.64" />
        <stop offset="0.6" stopColor="#fff" stopOpacity="0.24" />
        <stop offset="1" stopColor="#fff" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-height`} cx="50%" cy="50%" r="50%">
        {Array.from({ length: 65 }, (_, index) => {
          const t = index / 64;
          return <stop key={index} offset={t} stopColor="#fff" stopOpacity={Math.sqrt(1 - t * t)} />;
        })}
      </radialGradient>
      <filter id={`${id}-glaze`} x="-105" y="-105" width="210" height="210" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
        <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="height" />
        <feSpecularLighting in="height" surfaceScale="90" specularConstant="0.35" specularExponent="18" lightingColor="#fff" result="glaze">
          <fePointLight data-pebble-lamp="" x="-130" y="-170" z="220" />
        </feSpecularLighting>
        <feComposite in="glaze" in2="SourceAlpha" operator="in" />
      </filter>
      <filter id={`${id}-diffuse`} x="-105" y="-105" width="210" height="210" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
        <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="height" />
        <feDiffuseLighting in="height" surfaceScale="90" diffuseConstant="1" lightingColor="#fff" result="diffuse">
          <fePointLight data-pebble-lamp="" x="-130" y="-170" z="220" />
        </feDiffuseLighting>
        <feComposite in="diffuse" in2="SourceAlpha" operator="in" />
      </filter>
      <filter id={`${id}-grain`} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.72" numOctaves="3" seed="17" result="noise" />
        <feColorMatrix in="noise" type="saturate" values="0" />
        <feComponentTransfer><feFuncA type="linear" slope="0.075" /></feComponentTransfer>
        <feComposite in2="SourceGraphic" operator="in" />
        <feBlend in="SourceGraphic" mode="soft-light" />
      </filter>
      <filter id={`${id}-ground`} x="-60%" y="-200%" width="240%" height="500%"><feGaussianBlur stdDeviation={radius * 0.13} /></filter>
      <filter id={`${id}-contact`} x="-70%" y="-250%" width="240%" height="600%"><feGaussianBlur stdDeviation={radius * 0.055} /></filter>
      <clipPath id={`${id}-clip`}><path d={PEBBLE_OUTLINE} /></clipPath>
    </defs>
    <g data-pebble-ground="" aria-hidden="true">
      <ellipse data-pebble-shadow="" cx={radius * 0.1} cy={radius * 0.91} rx={radius * 0.88} ry={radius * 0.19} fill="#364755" opacity="0.25" filter={`url(#${id}-ground)`} />
      <ellipse data-pebble-contact="" cx={radius * 0.025} cy={radius * 0.91} rx={radius * 0.48} ry={radius * 0.08} fill="#31434a" opacity="0.21" filter={`url(#${id}-contact)`} />
    </g>
    <g data-pebble-body="" opacity="0.9">
      <g transform={`scale(${radius / 100})`}>
        <circle data-pebble-bounds="" r="100" fill="transparent" pointerEvents="none" />
        <g clipPath={`url(#${id}-clip)`}>
          <MapShapeGeometry radius={100} shape="pebble" data-pebble-silhouette="" fill={`url(#${id}-body)`} filter={`url(#${id}-grain)`} />
          {segments && segments.length > 1 && segments.map((segment, index) => <path key={index} data-pebble-segment={index} data-segment-color={segment} d={segmentPaths[index]} fill={`url(#${id}-segment-${index})`} />)}
          <path d={PEBBLE_OUTLINE} fill={`url(#${id}-shade)`} />
          <path d={PEBBLE_OUTLINE} fill={`url(#${id}-crown)`} />
          <path d={PEBBLE_OUTLINE} fill={`url(#${id}-window)`} />
          <path d={PEBBLE_OUTLINE} fill={`url(#${id}-height)`} filter={`url(#${id}-diffuse)`} opacity="0.18" style={{ mixBlendMode: "multiply" }} />
          <path d={PEBBLE_OUTLINE} fill={`url(#${id}-height)`} filter={`url(#${id}-glaze)`} />
          <ellipse data-highlight="" cx="-43" cy="-57" rx="20" ry="46" transform="rotate(42 -43 -57)" fill={`url(#${id}-glint)`} />
          <path d="M -84 -29 C -72 -61 -45 -86 -12 -92" stroke="#f3ffff" strokeWidth="1.2" strokeOpacity="0.58" fill="none" />
          <path d="M -59 72 C -24 97 29 98 61 72" stroke={paint.light} strokeWidth="2.5" strokeOpacity="0.16" fill="none" />
        </g>
        <MapEdgeFlow radius={100} shape="pebble" />
      </g>
    </g>
  </g>;
}
