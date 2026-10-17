import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vitest/config";

const labRoot = path.dirname(fileURLToPath(import.meta.url));
const casesDir = path.resolve(labRoot, "../../tests/fixtures/benchmark/cases");

/** Serves every person file named lab_nodes.json under the research cases directory. */
function labCases(): Plugin {
  return {
    name: "lab-cases",
    configureServer(server) {
      server.middlewares.use("/lab-cases", (_req, res) => {
        const people: unknown[] = [];
        if (fs.existsSync(casesDir)) {
          for (const entry of fs.readdirSync(casesDir, { withFileTypes: true })) {
            if (!entry.isDirectory()) continue;
            const file = path.join(casesDir, entry.name, "lab_nodes.json");
            if (!fs.existsSync(file)) continue;
            try {
              people.push(JSON.parse(fs.readFileSync(file, "utf8")));
            } catch {
              // One unreadable person file stays out of the list.
            }
          }
        }
        people.sort((left, right) => {
          const a = typeof left === "object" && left && "caseId" in left ? String(left.caseId) : "";
          const b = typeof right === "object" && right && "caseId" in right ? String(right.caseId) : "";
          return a.localeCompare(b);
        });
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(people));
      });
    },
  };
}

export default defineConfig({
  plugins: [labCases()],
  server: {
    fs: {
      allow: [labRoot, path.resolve(labRoot, "../../tests/fixtures/benchmark")],
    },
  },
  test: {
    include: ["tests/**/*.test.ts"],
    testTimeout: 180_000,
  },
});
