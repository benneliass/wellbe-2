import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const root = new URL("../../../tests/fixtures/benchmark/cases/", import.meta.url);

describe("person note keywords", () => {
  const files = readdirSync(root)
    .sort()
    .map((dir) => JSON.parse(readFileSync(new URL(`${dir}/lab_nodes.json`, root), "utf8")) as {
      label: string;
      nodes: Array<{ id: string; text: string; keyword: string }>;
    });

  it("gives every note a short keyword already in its text", () => {
    expect(files.length).toBe(5);
    for (const file of files) {
      expect(file.nodes.length).toBeGreaterThan(0);
      for (const node of file.nodes) {
        expect(node.keyword, node.id).toMatch(/^[A-Za-z0-9-]{1,6}$/);
        expect(node.text.toLowerCase(), node.id).toContain(node.keyword.toLowerCase());
        expect(node.keyword.toLowerCase(), node.id).not.toBe("new");
      }
    }
  });
});
