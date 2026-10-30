/** SVG matrices can describe the previous rendered frame just after a React
 * layout commit. Audit painted geometry, without an arbitrary timing delay.
 */
export function afterMapPaint(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
}

/** Audit the actual rendered SVG, including transforms, fonts, and curved paths. */
export function inspectMapGeometry() {
  const graph = Boolean(document.querySelector('[data-node-id]'));
  const selector = graph ? '[data-node-id]' : '[data-record-id]';
  const nodes = [...document.querySelectorAll<SVGGElement>(selector)].map((element) => {
    const material = element.querySelector<SVGCircleElement>('[data-porcelain-surface] circle');
    const circle = material ?? element.querySelector<SVGCircleElement>('circle')!;
    const matrix = circle.getScreenCTM()!;
    const point = new DOMPoint(Number(circle.getAttribute('cx') ?? 0), Number(circle.getAttribute('cy') ?? 0)).matrixTransform(matrix);
    const radius = Number(circle.getAttribute('r')) - (graph && !material ? 15 : 0);
    return { id: element.getAttribute(graph ? 'data-node-id' : 'data-record-id'), x: point.x, y: point.y, r: radius * Math.hypot(matrix.a, matrix.b), labels: [...element.querySelectorAll('text')].map((label) => label.getBoundingClientRect()), protectedLabels: [...element.querySelectorAll('text')].every((label) => { const style = getComputedStyle(label); return style.paintOrder.startsWith('stroke') && parseFloat(style.strokeWidth) >= 2.5; }) };
  });
  const overlaps: string[] = [];
  for (let i = 0; i < nodes.length; i += 1) for (let j = i + 1; j < nodes.length; j += 1) {
    const a = nodes[i]!; const b = nodes[j]!;
    if (Math.hypot(a.x - b.x, a.y - b.y) < a.r + b.r + 1) overlaps.push(`${a.id}/${b.id}: circles`);
    for (const label of a.labels) {
      if (b.x + b.r > label.x && b.x - b.r < label.right && b.y + b.r > label.y && b.y - b.r < label.bottom) overlaps.push(`${a.id}/${b.id}: label/circle`);
      for (const other of b.labels) if (label.x < other.right && label.right > other.x && label.y < other.bottom && label.bottom > other.y) overlaps.push(`${a.id}/${b.id}: labels`);
    }
    for (const label of b.labels) if (a.x + a.r > label.x && a.x - a.r < label.right && a.y + a.r > label.y && a.y - a.r < label.bottom) overlaps.push(`${b.id}/${a.id}: label/circle`);
  }
  const crossings: string[] = [];
  for (const path of document.querySelectorAll<SVGPathElement>('[data-connection]')) {
    const length = path.getTotalLength();
    const matrix = path.getScreenCTM()!;
    const source = path.getAttribute('data-source'); const target = path.getAttribute('data-target');
    for (const node of nodes) {
      let hit = false;
      for (let step = 2; step < 98; step += 1) {
        const point = path.getPointAtLength(length * step / 100);
        const screen = new DOMPoint(point.x, point.y).matrixTransform(matrix);
        if (node.id !== source && node.id !== target && Math.hypot(screen.x - node.x, screen.y - node.y) < node.r + 1) hit = true;
        if (!node.protectedLabels && node.labels.some((label) => screen.x > label.x - 1 && screen.x < label.right + 1 && screen.y > label.y - 1 && screen.y < label.bottom + 1)) hit = true;
      }
      if (hit) crossings.push(`${source}/${target} through ${node.id}`);
    }
  }
  return { overlaps, crossings, nodes: nodes.length };
}

/** A frame sample detects geometric jumps even when SVG command letters stay unchanged. */
export function sampleConnectionGeometry() {
  return [...document.querySelectorAll<SVGPathElement>('[data-connection]')].map((path) => {
    const length = path.getTotalLength();
    return {
      id: `${path.getAttribute('data-source')}/${path.getAttribute('data-target')}`,
      plans: Number(path.getAttribute('data-route-plans') ?? path.closest('[data-silk-link]')?.getAttribute('data-route-plans') ?? 0),
      commands: path.getAttribute('d')?.replace(/[^MLCQ]/g, ''),
      points: Array.from({ length: 17 }, (_, i) => {
        const point = path.getPointAtLength(length * i / 16);
        return { x: point.x, y: point.y };
      }),
    };
  });
}

/** Measure the visible turn over 12px of thread, including obstacle-route joins. */
export function inspectConnectionBends() {
  let worst = { radians: 0, edge: "" };
  for (const path of document.querySelectorAll<SVGPathElement>('[data-connection]')) {
    const length = path.getTotalLength();
    for (let along = 6; along < length - 6; along += 2) {
      const a = path.getPointAtLength(along - 6);
      const b = path.getPointAtLength(along);
      const c = path.getPointAtLength(along + 6);
      const ux = b.x - a.x, uy = b.y - a.y, vx = c.x - b.x, vy = c.y - b.y;
      const radians = Math.acos(Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (Math.hypot(ux, uy) * Math.hypot(vx, vy) || 1))));
      if (radians > worst.radians) worst = { radians, edge: `${path.dataset.source}/${path.dataset.target}` };
    }
  }
  return worst;
}
