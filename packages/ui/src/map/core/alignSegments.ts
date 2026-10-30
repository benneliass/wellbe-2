import { bridgeArcPaths, bridgeFillPaths, type BridgeBearing } from "./segments";

/** Attach the color fields to real rendered ports, including hover tilt and drag deformation. */
export function alignSegmentedMaterial(node: SVGGElement, links: readonly SVGGElement[], now: number, calm: boolean) {
  const cases: string[] = JSON.parse(node.getAttribute('data-map-segment-keys') ?? '[]');
  if (cases.length < 2 || typeof DOMPoint === 'undefined') return;
  const bounds = node.querySelector<SVGCircleElement>('[data-pebble-bounds]');
  const accents = node.querySelector<SVGGElement>('[data-node-accents="bridge"]');
  const fillMatrix = bounds?.getCTM?.(), accentMatrix = accents?.getCTM?.();
  if (!fillMatrix || !accentMatrix) return;
  const fillInverse = fillMatrix.inverse(), accentInverse = accentMatrix.inverse();
  const fill: BridgeBearing[] = [], arcs: BridgeBearing[] = [];
  const id = node.getAttribute('data-map-object-id');
  for (const link of links) {
    const end = link.getAttribute('data-source') === id ? 'source' : link.getAttribute('data-target') === id ? 'target' : null;
    if (!end) continue;
    const index = cases.indexOf(link.getAttribute(`data-${end}-segment`) ?? '');
    const rawX = link.getAttribute(`data-${end}-port-x`), rawY = link.getAttribute(`data-${end}-port-y`);
    const matrix = link.getCTM?.();
    if (index < 0 || rawX === null || rawY === null || !matrix) continue;
    const port = new DOMPoint(Number(rawX), Number(rawY)).matrixTransform(matrix);
    const localFill = port.matrixTransform(fillInverse), localArc = port.matrixTransform(accentInverse);
    fill.push({ index, angle: Math.atan2(localFill.y, localFill.x) });
    arcs.push({ index, angle: Math.atan2(localArc.y, localArc.x) });
  }
  const fallback: BridgeBearing[] = JSON.parse(node.getAttribute('data-map-segment-fallback') ?? '[]');
  for (const bearing of fallback) if (!fill.some((item) => item.index === bearing.index)) { fill.push(bearing); arcs.push(bearing); }
  const paths = bridgeFillPaths(cases.length, fill);
  node.querySelectorAll<SVGPathElement>('[data-pebble-segment]').forEach((path) => {
    const index = Number(path.getAttribute('data-pebble-segment'));
    path.setAttribute('d', paths[index] ?? '');
    path.setAttribute('data-segment-key', cases[index] ?? '');
  });
  const radius = Number(node.getAttribute('data-pebble-radius')) + 4;
  const arcPaths = bridgeArcPaths(cases.length, radius, arcs, calm ? 0 : Math.sin(now * 0.0004) * 0.025);
  accents?.querySelectorAll<SVGPathElement>('[data-bridge-accent]').forEach((path) => path.setAttribute('d', arcPaths[Number(path.getAttribute('data-bridge-accent'))] ?? ''));
}
