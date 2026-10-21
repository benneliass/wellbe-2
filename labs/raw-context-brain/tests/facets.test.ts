import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ALLOWED_FACET_LABELS,
  PICTURE_CONTRACT,
  ROUTE_KINDS,
  assertPictureContract,
  isAllowedRouteLabel,
} from "../src/facets.js";

const labRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const LEGEND = [
  "<p class=\"legend\">",
  "A line is an association. A larger circle is the number of links. This is not a diagnosis.",
  "</p>",
].join("");

describe("navigation facets", () => {
  it("locks route kinds to neighbour, facet, temporal, source, and fallback", () => {
    expect([...ROUTE_KINDS]).toEqual(["neighbour", "facet", "temporal", "source", "fallback"]);
  });

  it("recognizes the fixed labels, a record-kind facet, and a varying neighbour", () => {
    expect([...ALLOWED_FACET_LABELS]).toEqual([
      "Earlier context",
      "Later context",
      "Original record",
      "Stop here",
    ]);
    for (const label of ALLOWED_FACET_LABELS) {
      expect(isAllowedRouteLabel(label)).toBe(true);
    }
    expect(isAllowedRouteLabel("Only notes")).toBe(true);
    expect(isAllowedRouteLabel("Only results")).toBe(true);
    expect(isAllowedRouteLabel("Open lentil soup")).toBe(true);
    expect(isAllowedRouteLabel("Only note")).toBe(false);
    expect(isAllowedRouteLabel("lentil soup")).toBe(false);
  });

  it("rejects a label that names a diagnosis, cause, severity, symptom, or problem list", () => {
    const rejected = [
      "Only diagnosis",
      "Only CAUSES",
      "Only high severity notes",
      "Only symptoms",
      "Only problem lists",
      "Open the Diagnosis note",
      "Earlier context because",
    ];
    for (const label of rejected) {
      expect(isAllowedRouteLabel(label)).toBe(false);
    }
  });

  it("holds the picture on disk to undirected associations", () => {
    const html = readFileSync(resolve(labRoot, "index.html"), "utf8");
    const graphSource = readFileSync(resolve(labRoot, "src/viz/main.ts"), "utf8");
    expect(PICTURE_CONTRACT.lines).toBe("undirected associations");
    expect(PICTURE_CONTRACT.color).toBe("record kind");
    expect(PICTURE_CONTRACT.size).toBe("number of links");
    expect([...PICTURE_CONTRACT.legend]).toEqual([
      "A line is an association",
      "the number of links",
      "not a diagnosis",
    ]);
    expect(() => assertPictureContract(html, graphSource)).not.toThrow();
  });

  it("throws when the legend drops a phrase or the graph draws a direction", () => {
    const graphSource = readFileSync(resolve(labRoot, "src/viz/main.ts"), "utf8");
    expect(() => assertPictureContract("<p class=\"legend\">Color is the kind of record.</p>", graphSource)).toThrow(
      /legend misses/,
    );
    const outside =
      "<p>A line is an association. A larger circle is the number of links. This is not a diagnosis.</p><p class=\"legend\">Color only.</p>";
    expect(() => assertPictureContract(outside, graphSource)).toThrow(/legend misses/);
    expect(() => assertPictureContract(LEGEND, `${graphSource}\nlinkArrows: true`)).toThrow(/linkArrows/);
    expect(() => assertPictureContract(LEGEND, `${graphSource}\narrowSize: 8`)).toThrow(/arrowSize/);
    expect(() => assertPictureContract(LEGEND, `${graphSource}\nthis leads to that`)).toThrow(/leads to/);
  });
});
