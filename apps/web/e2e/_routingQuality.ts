/** Measures the drawn SVG rather than trusting the router's intended path. */
export function inspectRoutingQuality() {
  const edges = [...document.querySelectorAll<SVGPathElement>('[data-connection]')].filter((path) => path.getAttribute('d')).map((path) => {
    const length = path.getTotalLength(), matrix = path.getScreenCTM()!;
    const count = Math.max(40, Math.ceil(length / 3));
    const points = Array.from({ length: count + 1 }, (_, i) => {
      const p = path.getPointAtLength(length * i / count);
      return { x: p.x, y: p.y };
    });
    const start = points[0]!, end = points.at(-1)!;
    return { id: `${path.getAttribute('data-source')}/${path.getAttribute('data-target')}`, source: path.getAttribute('data-source'), target: path.getAttribute('data-target'), length, ratio: length / Math.max(1, Math.hypot(end.x - start.x, end.y - start.y)), points, matrix };
  });
  const crossings: string[] = [], overlaps: string[] = [];
  const side = (a: { x: number; y: number }, b: { x: number; y: number }, c: { x: number; y: number }) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  for (let i = 0; i < edges.length; i++) for (let j = i + 1; j < edges.length; j++) {
    const a = edges[i]!, b = edges[j]!;
    let crossing = false, overlap = 0;
    for (let u = 2; u < a.points.length - 3; u++) {
      const p = a.points[u]!, q = a.points[u + 1]!;
      let close = false;
      for (let v = 2; v < b.points.length - 3; v++) {
        const r = b.points[v]!, s = b.points[v + 1]!;
        if (side(p, q, r) * side(p, q, s) < -0.0001 && side(r, s, p) * side(r, s, q) < -0.0001) crossing = true;
        const dx = q.x - p.x, dy = q.y - p.y, ex = s.x - r.x, ey = s.y - r.y;
        if (Math.hypot(p.x - r.x, p.y - r.y) < 4 && Math.abs(dx * ey - dy * ex) / (Math.hypot(dx, dy) * Math.hypot(ex, ey) || 1) < 0.15) close = true;
      }
      if (close) overlap += Math.hypot(q.x - p.x, q.y - p.y);
    }
    if (crossing) crossings.push(`${a.id} × ${b.id}`);
    if (overlap > 24) overlaps.push(`${a.id} / ${b.id}: ${Math.round(overlap)}px`);
  }
  const obstructions: string[] = [], underLabels: string[] = [];
  for (const edge of edges) for (const node of document.querySelectorAll<SVGGElement>('[data-node-id], [data-record-id]')) {
    const id = node.getAttribute('data-node-id') ?? node.getAttribute('data-record-id');
    const material = node.querySelector<SVGCircleElement>('[data-porcelain-surface] circle');
    const disc = material ?? node.querySelector<SVGCircleElement>('circle');
    if (!disc) continue;
    const matrix = disc.getScreenCTM()!;
    const center = new DOMPoint(Number(disc.getAttribute('cx') ?? 0), Number(disc.getAttribute('cy') ?? 0)).matrixTransform(matrix);
    const cx = center.x, cy = center.y, radius = (Number(disc.getAttribute('r')) - (material ? 0 : 15)) * Math.hypot(matrix.a, matrix.b);
    const labels = [...node.querySelectorAll('text')].map((text) => text.getBoundingClientRect());
    const hit = edge.points.slice(2, -2).some((point) => {
      const p = new DOMPoint(point.x, point.y).matrixTransform(edge.matrix);
      return id !== edge.source && id !== edge.target && Math.hypot(p.x - cx, p.y - cy) < radius;
    });
    if (hit) obstructions.push(`${edge.id} through ${id}`);
    if (edge.points.some((point) => { const p = new DOMPoint(point.x, point.y).matrixTransform(edge.matrix); return labels.some((label) => p.x > label.left && p.x < label.right && p.y > label.top && p.y < label.bottom); })) underLabels.push(`${edge.id} beneath ${id}`);
  }
  const lengths = edges.map(({ id, length, ratio }) => ({ id, length: Math.round(length * 10) / 10, detour: Math.round(ratio * 1000) / 1000 }));
  return { edges: edges.length, totalLength: Math.round(edges.reduce((sum, edge) => sum + edge.length, 0)), maxDetour: Math.max(...lengths.map((edge) => edge.detour)), crossings, overlaps, obstructions, underLabels, lengths };
}
