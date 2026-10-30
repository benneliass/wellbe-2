import { expect, test, type Page } from "@playwright/test";
import { injectSession } from "./_session";
import { inspectMapGeometry, sampleConnectionGeometry, inspectConnectionBends, afterMapPaint } from "./_mapGeometry";

const orb = (page: Page, name: string) => page.getByRole("button", { name, exact: true });
const record = (page: Page, id: string) => page.locator(`[data-record-id="${id}"]`);
async function center(page: Page, id: string) {
  const box = await record(page, id).locator('[data-pebble-bounds]').boundingBox();
  if (!box) throw new Error(`Missing record ${id}`);
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

test.beforeEach(async ({ page }) => {
  await injectSession(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/context?preview=design");
  await expect(orb(page, "Monday note")).toBeVisible();
  await page.waitForFunction(() => {
    const scene = document.querySelector<SVGSVGElement>('svg[aria-label="Your records context map"]');
    return scene && Math.abs(scene.viewBox.baseVal.width - scene.getBoundingClientRect().width) < 1;
  });
  await page.evaluate(afterMapPaint);
});

test("walk, filters, rewind, stop, and clear retain their meanings", async ({ page }) => {
  await expect(page.locator('[data-record-id]')).toHaveCount(10);
  const before = await record(page, "r01").getAttribute("transform");
  await orb(page, "Monday note").click();
  await expect(record(page, "r01")).toHaveAttribute("transform", before!);
  await expect(record(page, "r04")).toHaveAttribute("data-dim", "true");
  await page.getByRole("button", { name: "Only notes", exact: true }).click();
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "true");
  await orb(page, "Sleep note").click();
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Open r02", exact: true }).click();
  await expect(orb(page, "Visit summary")).toHaveAttribute("aria-pressed", "true");
  await expect(record(page, "r01")).toHaveAttribute("transform", before!);
  await orb(page, "Monday note").click();
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Stop here", exact: true }).click();
  await expect(page.getByRole("button", { name: "Open r02", exact: true })).toHaveCount(0);
  await orb(page, "Visit summary").click();
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Clear choice", exact: true }).click();
  await expect(record(page, "r04")).toHaveAttribute("data-dim", "false");
});

test("drag bends attached links without selecting; labels are not controls", async ({ page }) => {
  const point = await center(page, "r01");
  const edge = page.locator('[data-connection]').first();
  const before = await edge.getAttribute("d");
  const distant = await record(page, "r09").getAttribute("transform");
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  await page.mouse.move(point.x + 80, point.y + 35, { steps: 8 });
  await page.mouse.up();
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "false");
  await expect(edge).not.toHaveAttribute("d", before!);
  await expect(record(page, "r09")).toHaveAttribute("transform", distant!);
  await record(page, "r01").locator("text").click({ force: true });
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "false");
  await orb(page, "Monday note").focus();
  await page.keyboard.press("Enter");
  await expect(orb(page, "Monday note")).toHaveAttribute("aria-pressed", "true");
});

test("hover lifts the object and attached label; reduced motion freezes drift", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const point = await center(page, "r02");
  const labelY = await record(page, "r02").locator("text").getAttribute("y");
  await page.mouse.move(point.x, point.y);
  await expect(record(page, "r02")).toHaveAttribute("data-hot", "true");
  await expect.poll(() => record(page, 'r02').locator('[data-pebble-object]').getAttribute('transform')).not.toBe("translate(0 0)");
  await expect(record(page, "r02").locator("text")).toHaveAttribute("y", labelY!);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(record(page, 'r02').locator('[data-pebble-object]')).toHaveAttribute('transform', 'translate(0 0)');
  const frozen = await record(page, "r01").getAttribute("transform");
  // A second browser rendering frame must leave reduced-motion geometry unchanged.
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(record(page, "r01")).toHaveAttribute("transform", frozen!);
});

test("phone map keeps controls large and content inside the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForFunction(() => {
    const scene = document.querySelector<SVGSVGElement>('svg[aria-label="Your records context map"]');
    return scene && Math.abs(scene.viewBox.baseVal.width - scene.getBoundingClientRect().width) < 1;
  });
  await expect(orb(page, "Monday note")).toBeVisible();
  const box = await orb(page, "Monday note").boundingBox();
  expect(box?.width).toBeGreaterThanOrEqual(44);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await orb(page, "Monday note").click();
  await page.getByRole("button", { name: "Open r02", exact: true }).click();
  await expect(orb(page, "Visit summary")).toHaveAttribute("aria-pressed", "true");
});

test("live records use the porcelain renderer without sample data or study panels", async ({ page }) => {
  const records = ["Morning note", "Visit document", "Lab report", "Sleep record", "Questions", "Voice recording"].map((label, index) => ({
    id: `live-${index}`, label, kind: "event", source_type: ["note", "document", "result", "note", "note", "audio"][index], degree: index === 0 ? 4 : 1,
  }));
  await page.route("**/v2/context/map", (route) => route.fulfill({ json: {
    nodes: records, links: records.slice(1).map((node) => ({ source: "live-0", target: node.id, reason: "may relate" })),
  } }));
  await page.goto("/context");
  await expect(orb(page, "Morning note")).toBeVisible();
  await expect(page.getByText("Design preview", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("complementary", { name: "Interaction design details" })).toHaveCount(0);
  await page.evaluate(afterMapPaint);
  const boxes = await page.locator('[data-record-id] [data-pebble-bounds]').evaluateAll((elements) => elements.map((element) => {
    const rect = element.getBoundingClientRect(); return { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom };
  }));
  for (let left = 0; left < boxes.length; left += 1) {
    for (let right = left + 1; right < boxes.length; right += 1) {
      const a = boxes[left]!; const b = boxes[right]!;
      expect(a.right <= b.x || b.right <= a.x || a.bottom <= b.y || b.bottom <= a.y).toBe(true);
    }
  }
});

test("ambient curves move, the current step has a sheen, and reduced motion freezes both", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const line = page.locator('[data-connection]').first();
  const restingCurve = await line.getAttribute("d");
  await expect.poll(() => line.getAttribute("d")).not.toBe(restingCurve);
  await orb(page, "Monday note").focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Open r02", exact: true }).click();
  const sheen = page.locator('[data-link-flow]');
  await expect(sheen).toHaveCount(1);
  expect(await sheen.evaluate((element) => getComputedStyle(element).animationName)).not.toBe("none");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(sheen).toHaveCount(0);
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  const still = await line.getAttribute("d");
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(line).toHaveAttribute("d", still!);
});


test("full and opened map geometry stays clear on desktop and phone", async ({ page }) => {
  for (const width of [1774, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.waitForFunction(() => {
      const scene = document.querySelector<SVGSVGElement>('svg[aria-label="Your records context map"]');
      return scene && Math.abs(scene.viewBox.baseVal.width - scene.getBoundingClientRect().width) < 1;
    });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(afterMapPaint);
    const full = await page.evaluate(inspectMapGeometry);
    expect(full.overlaps).toEqual([]);
    expect(full.crossings).toEqual([]);
    await orb(page, "Monday note").focus();
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Open r02", exact: true }).click();
    await page.evaluate(afterMapPaint);
    const opened = await page.evaluate(inspectMapGeometry);
    expect(opened.overlaps).toEqual([]);
    expect(opened.crossings).toEqual([]);
    await page.getByRole("button", { name: "Clear choice", exact: true }).click();
  }
});


test("held links stay continuous through a drag and settle elastically after release", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const point = await center(page, "r02");
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  let previous = await page.evaluate(sampleConnectionGeometry);
  const plans = previous.map((edge) => edge.plans);
  let maxJump = 0;
  for (let step = 1; step <= 40; step += 1) {
    await page.mouse.move(point.x + Math.sin(step / 40 * Math.PI) * 90, point.y + step / 40 * 55);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
    const current = await page.evaluate(sampleConnectionGeometry);
    expect(current.map((edge) => edge.plans)).toEqual(plans);
    for (let edge = 0; edge < current.length; edge += 1) {
      expect(current[edge]!.commands).toBe(previous[edge]!.commands);
      for (let i = 1; i < 16; i += 1) maxJump = Math.max(maxJump, Math.hypot(current[edge]!.points[i]!.x - previous[edge]!.points[i]!.x, current[edge]!.points[i]!.y - previous[edge]!.points[i]!.y));
    }
    previous = current;
  }
  expect(maxJump).toBeLessThan(18);
  const releaseCurve = await page.locator('[data-connection][data-target="r02"]').first().getAttribute("d");
  await page.mouse.up();
  await expect.poll(() => page.locator('[data-connection][data-target="r02"]').first().getAttribute("d")).not.toBe(releaseCurve);
  await expect(orb(page, "Visit summary")).toHaveAttribute("aria-pressed", "false");
});

test("opening every record at the narrow preview width keeps threads smooth and clear", async ({ page }) => {
  await page.setViewportSize({ width: 689, height: 1000 });
  await page.waitForFunction(() => (() => { const scene = document.querySelector<SVGSVGElement>('svg[aria-label="Your records context map"]'); return scene && Math.abs(scene.viewBox.baseVal.width - scene.getBoundingClientRect().width) < 1; })());
  for (const id of ["r01", "r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09", "r10"]) {
    await record(page, id).locator('[data-object]').focus();
    await page.keyboard.press("Enter");
    await page.evaluate(afterMapPaint);
    const geometry = await page.evaluate(inspectMapGeometry);
    expect(geometry.overlaps, id).toEqual([]);
    expect(geometry.crossings, id).toEqual([]);
    const bend = await page.evaluate(inspectConnectionBends);
    expect(bend.radians, `${id}: ${bend.edge}`).toBeLessThan(0.55);
    await page.getByRole("button", { name: "Clear choice", exact: true }).click();
  }
  for (const id of ["r01", "r02", "r06"]) {
    await record(page, id).locator('[data-object]').focus();
    await page.keyboard.press("Enter");
  }
  await page.evaluate(afterMapPaint);
  const geometry = await page.evaluate(inspectMapGeometry);
  expect(geometry.overlaps).toEqual([]);
  expect(geometry.crossings).toEqual([]);
  expect((await page.evaluate(inspectConnectionBends)).radians).toBeLessThan(0.55);
});

test("threads do not fold back during the animated neighbour hop", async ({ page }) => {
  await page.setViewportSize({ width: 689, height: 1000 });
  await page.waitForFunction(() => (() => { const scene = document.querySelector<SVGSVGElement>('svg[aria-label="Your records context map"]'); return scene && Math.abs(scene.viewBox.baseVal.width - scene.getBoundingClientRect().width) < 1; })());
  await page.emulateMedia({ reducedMotion: "no-preference" });
  for (const id of ["r01", "r02", "r06"]) {
    await record(page, id).locator('[data-object]').focus();
    await page.keyboard.press("Enter");
    const bends: number[] = [];
    const until = Date.now() + 1100;
    while (Date.now() < until) {
      bends.push((await page.evaluate(inspectConnectionBends)).radians);
      await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
    }
    expect(Math.max(...bends), id).toBeLessThan(0.7);
  }
});
