import { describe, expect, it } from "vitest";
import { generateTopology } from "../src/generate.js";
import { HnswIndex } from "../src/hnsw.js";
import { mulberry32, tokenVector } from "../src/text.js";

describe("scale and approximate recall", () => {
  it("keeps exploration payloads bounded as the map grows", () => {
    const sizes = [100, 1_000, 10_000];
    for (const count of sizes) {
      const started = Date.now();
      const lab = generateTopology({ count, kind: "sparse", seed: 9 });
      const response = lab.explore({
        personId: "synthetic-1",
        purpose: "nav",
        anchorId: "n1",
      });
      const bytes = new TextEncoder().encode(JSON.stringify(response)).length;
      expect(response.items.length).toBeLessThanOrEqual(5);
      expect(bytes).toBeLessThan(16_000);
      expect(lab.metrics.crossPersonCandidates).toBe(0);
      expect(Date.now() - started).toBeLessThan(30_000);
    }
  });

  it("terminates sparse, dense, cyclic, and hub maps", () => {
    for (const kind of ["sparse", "dense", "cyclic", "hub"] as const) {
      const lab = generateTopology({ count: 80, kind, seed: 11 });
      let response = lab.explore({
        personId: "synthetic-1",
        purpose: "nav",
        anchorId: kind === "hub" ? "n1" : "n0",
      });
      for (let step = 0; step < 20 && response.routeHandle; step += 1) {
        response = lab.explore({
          personId: "synthetic-1",
          purpose: "nav",
          routeHandle: response.routeHandle,
        });
        expect(response.items.length).toBeLessThanOrEqual(5);
      }
      expect(response.terminalReason).not.toBeNull();
      expect(response.detail.toLowerCase()).not.toContain("no relevant context");
    }
  });

  it("recalls most exact neighbours from the approximate index", () => {
    const index = new HnswIndex(12, 16);
    const random = mulberry32(12);
    const vectors: Float64Array[] = [];
    for (let cluster = 0; cluster < 8; cluster += 1) {
      const center = Float64Array.from({ length: 16 }, () => random() * 2 - 1);
      for (let member = 0; member < 25; member += 1) {
        const vector = Float64Array.from(center, (value) => value + (random() - 0.5) * 0.05);
        let norm = 0;
        for (const value of vector) norm += value * value;
        norm = Math.sqrt(norm);
        for (let dim = 0; dim < vector.length; dim += 1) vector[dim] /= norm;
        const id = `c${cluster}-${member}`;
        vectors.push(vector);
        index.add(id, vector);
      }
    }
    let hits = 0;
    let total = 0;
    for (let query = 0; query < 20; query += 1) {
      const cluster = query % 8;
      const member = query % 25;
      const id = `c${cluster}-${member}`;
      const vector = vectors[cluster * 25 + member];
      const exact = new Set(index.bruteForce(vector, 5, id).map((item) => item.id));
      const approx = new Set(
        index
          .search(vector, 10)
          .map((item) => item.id)
          .filter((item) => item !== id),
      );
      for (const neighbor of exact) {
        total += 1;
        if (approx.has(neighbor)) hits += 1;
      }
    }
    expect(hits / total).toBeGreaterThan(0.7);
    expect(tokenVector("sample", 16).length).toBe(16);
  });
});
