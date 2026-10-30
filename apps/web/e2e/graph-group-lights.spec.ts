import { expect, test } from '@playwright/test';
import { afterMapPaint } from './_mapGeometry';

/** Audit rendered footprints, including the full orbit rather than just today's dot positions. */
function groupCoverage() {
  const outside: string[] = [];
  const lights: Record<string, { cx: number; cy: number; rx: number; ry: number; members: string[] }> = {};
  for (const group of document.querySelectorAll<SVGGElement>('[data-map-group-light]')) {
    const ellipse = group.querySelector<SVGEllipseElement>('[data-group-light]')!;
    const id = ellipse.getAttribute('data-group-light')!;
    const layout = JSON.parse(group.getAttribute('data-group-layout')!);
    const cx = Number(ellipse.getAttribute('cx')), cy = Number(ellipse.getAttribute('cy'));
    const rx = Number(ellipse.getAttribute('rx')), ry = Number(ellipse.getAttribute('ry'));
    const inverse = ellipse.getScreenCTM()!.inverse();
    const check = (point: DOMPoint, member: string) => {
      const p = point.matrixTransform(inverse);
      if (Math.hypot((p.x - cx) / rx, (p.y - cy) / ry) > 0.905) outside.push(`${id}/${member}: q=${Math.hypot((p.x - cx) / rx, (p.y - cy) / ry).toFixed(4)}, point=${p.x.toFixed(2)},${p.y.toFixed(2)}, ellipse=${cx},${cy},${rx},${ry}`);
    };
    for (const member of layout.members as string[]) {
      const node = [...document.querySelectorAll('[data-map-object-id]')].find((node) => node.getAttribute('data-map-object-id') === member)!;
      if (!node) { outside.push(`${id}/missing:${member}`); continue; }
      for (const part of node.querySelectorAll('[data-pebble-body], text, [data-metadata-badge], [data-accent-envelope], [data-expanded-ring]')) {
        const r = part.getBoundingClientRect();
        if (!r.width && !r.height) continue;
        for (const x of [r.left, r.right]) for (const y of [r.top, r.bottom]) check(new DOMPoint(x, y), member);
      }
      const orbit = node.querySelector<SVGGElement>('[data-node-orbit]');
      if (orbit) {
        const radius = Number(orbit.getAttribute('data-orbit-extent'));
        for (const x of [-radius, radius]) for (const y of [-radius, radius]) check(new DOMPoint(x, y).matrixTransform(orbit.getScreenCTM()!), `${member}:orbit`);
      }
    }
    lights[id] = { cx, cy, rx, ry, members: layout.members };
  }
  return { outside: [...new Set(outside)], lights };
}

for (const width of [1774, 690, 390]) {
  test(`group lights cover all members and follow dragging at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    await expect(page.locator('[data-map-group-light]')).toHaveCount(3);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(afterMapPaint);
    const before = await page.evaluate(groupCoverage);
    expect(before.outside).toEqual([]);
    expect(before.lights.head!.members).toContain('dizzy');
    expect(before.lights.sleep!.members).toContain('dizzy');
    const headache = page.locator('[data-node-id="headache"]');
    await headache.press('Enter');
    await expect(headache.locator('[data-pebble-object]')).toHaveAttribute('data-pebble-scale', '1.3500');
    await page.evaluate(afterMapPaint);
    expect((await page.evaluate(groupCoverage)).outside).toEqual([]);
    const selected = (await page.evaluate(groupCoverage)).lights.head!;
    const light = page.locator('[data-node-id="light"]');
    const box = (await light.locator('[data-pebble-bounds]').boundingBox())!;
    const map = (await page.locator('svg[aria-label^="Map of your concerns"]').boundingBox())!;
    const from = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
    const to = { x: map.x + map.width - 32, y: map.y + map.height * 0.75 };
    await page.mouse.move(from.x, from.y); await page.mouse.down();
    for (let step = 1; step <= 30; step++) {
      await page.mouse.move(from.x + (to.x - from.x) * step / 30, from.y + (to.y - from.y) * step / 30);
      await page.evaluate(afterMapPaint);
      if (step % 5 === 0) expect((await page.evaluate(groupCoverage)).outside).toEqual([]);
    }
    await page.mouse.up(); await page.mouse.move(2, 2);
    await page.evaluate(afterMapPaint);
    const moved = await page.evaluate(groupCoverage);
    expect(moved.outside).toEqual([]);
    expect(Math.hypot(moved.lights.head!.cx - selected.cx, moved.lights.head!.cy - selected.cy)).toBeGreaterThan(10);
    if (width === 1774) await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/group-light-coverage/dragged.png' });
    await page.getByRole('button', { name: 'Reset layout', exact: true }).click();
    await page.evaluate(afterMapPaint);
    const reset = await page.evaluate(groupCoverage);
    expect(reset.outside).toEqual([]);
    // Other members retain their collision-safe derived homes after a drag.
    // Reset must refit the actual scene rather than restore an old halo.
    expect(Math.hypot(reset.lights.head!.cx - moved.lights.head!.cx, reset.lights.head!.cy - moved.lights.head!.cy)).toBeGreaterThan(10);
  });
}

test('touching group tints mix both colors without depending on paint order', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  await expect(page.locator('[data-map-group-light]')).toHaveCount(3);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(afterMapPaint);
  await expect(page.locator('[data-map-group-layer]')).toHaveCSS('isolation', 'isolate');
  for (const group of await page.locator('[data-map-group-light]').all()) await expect(group).toHaveCSS('mix-blend-mode', 'multiply');
  const colors = await page.evaluate(async () => {
    const ns = 'http://www.w3.org/2000/svg';
    const bridge = document.querySelector('[data-node-id="dizzy"]')!;
    const x = Math.round(Number(bridge.getAttribute('data-pebble-x'))), y = Math.round(Number(bridge.getAttribute('data-pebble-y')));
    const sample = async (ids: string[]) => {
      const svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('width', '1200'); svg.setAttribute('height', '1200');
      const background = document.createElementNS(ns, 'rect');
      background.setAttribute('width', '1200'); background.setAttribute('height', '1200'); background.setAttribute('fill', '#fcfdff'); svg.append(background);
      const layer = document.createElementNS(ns, 'g'); layer.style.isolation = 'isolate'; svg.append(layer);
      for (const id of ids) layer.append(document.querySelector(`[data-map-group-light="${id}"]`)!.cloneNode(true));
      const image = new Image();
      await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error('Could not rasterize group lights')); image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(svg))}`; });
      const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 1200;
      const ctx = canvas.getContext('2d')!; ctx.drawImage(image, 0, 0);
      return [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3);
    };
    return { head: await sample(['head']), sleep: await sample(['sleep']), mixed: await sample(['head', 'sleep']), reversed: await sample(['sleep', 'head']) };
  });
  for (let i = 0; i < 3; i++) expect(Math.abs(colors.mixed[i]! - colors.reversed[i]!)).toBeLessThanOrEqual(1);
  const difference = (a: number[], b: number[]) => a.reduce((sum, value, i) => sum + Math.abs(value - b[i]!), 0);
  expect(difference(colors.mixed, colors.head)).toBeGreaterThan(2);
  expect(difference(colors.mixed, colors.sleep)).toBeGreaterThan(2);
});
