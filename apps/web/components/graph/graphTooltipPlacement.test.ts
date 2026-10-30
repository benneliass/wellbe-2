import { describe, expect, it } from "vitest";
import { placeGraphTooltip, type TooltipRect } from "@wellbe/ui/map/core";

const touches = (a: TooltipRect, b: TooltipRect) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
describe('graph hover popup placement', () => {
  for (const anchor of [
    { left: 120, top: 120, right: 180, bottom: 180 },
    { left: 2, top: 2, right: 62, bottom: 62 },
    { left: 290, top: 300, right: 350, bottom: 360 },
  ]) it(`clears the object and its effects near ${anchor.left},${anchor.top}`, () => {
    const size = { width: 220, height: 58 }, bounds = { width: 360, height: 400 };
    const { x, y } = placeGraphTooltip(anchor, size, bounds, [anchor]);
    const popup = { left: x, top: y, right: x + size.width, bottom: y + size.height };
    expect(touches(anchor, popup)).toBe(false);
    expect(x).toBeGreaterThanOrEqual(10);
    expect(y).toBeGreaterThanOrEqual(10);
    expect(popup.right).toBeLessThanOrEqual(bounds.width - 10);
    expect(popup.bottom).toBeLessThanOrEqual(bounds.height - 10);
  });
  it('uses free space when the preferred side contains another object', () => {
    const anchor = { left: 150, top: 150, right: 210, bottom: 210 };
    const above = { left: 60, top: 50, right: 300, bottom: 145 };
    const size = { width: 220, height: 60 };
    const { x, y } = placeGraphTooltip(anchor, size, { width: 400, height: 450 }, [anchor, above]);
    const popup = { left: x, top: y, right: x + size.width, bottom: y + size.height };
    expect(touches(popup, anchor)).toBe(false);
    expect(touches(popup, above)).toBe(false);
  });
});
