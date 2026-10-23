import { describe, expect, it } from "vitest";
import {
  BrowserGraphStore,
  GRAPH_STORE_KEY,
  type DurableSnapshot,
  type GraphStorage,
} from "../src/persist/graph-store.js";
import { MemoryGraphStore } from "../src/persist/memory-store.js";
import { MemorySessionStore } from "../src/persist/session-store.js";

class MapStorage implements GraphStorage {
  private readonly items = new Map<string, string>();

  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

function sample(): DurableSnapshot {
  return {
    events: [
      {
        id: "e1",
        personId: "p1",
        capturedAt: "2024-01-02T00:00:00.000Z",
        sourceType: "note",
        text: "short sleep",
        contentHash: "h1",
        lineageId: "sleep",
        documentId: null,
      },
    ],
    advertisements: [
      {
        id: "ad-1",
        personId: "p1",
        sequence: 1,
        origin: "model",
        digest: "d1",
        modelVersion: null,
        promptVersion: null,
        policyVersion: "lab-policy-1",
        evidenceIds: ["e1"],
        fromId: "b",
        toId: "a",
        judgment: "link",
        reasonCode: "shared_terms",
        relation: "possible_semantic_association",
        proposedConfidence: 0.4,
        confidence: 0.4,
        createdAt: "2024-01-02T00:00:00.000Z",
        supersedesId: null,
        withdrawn: false,
      },
    ],
    nodes: [
      {
        id: "e1",
        kind: "event",
        vaultEventId: "e1",
        memberEventIds: [],
        personId: "p1",
      },
    ],
    acknowledgements: [
      {
        personId: "p1",
        endpointIds: ["b", "a"],
        acknowledged: true,
        updatedAt: "2024-01-03T00:00:00.000Z",
      },
    ],
  };
}

function stored(): DurableSnapshot {
  const snapshot = sample();
  snapshot.acknowledgements[0] = {
    ...snapshot.acknowledgements[0],
    endpointIds: ["a", "b"],
  };
  return snapshot;
}

describe("mock durable graph store", () => {
  it("round-trips events, advertisements, nodes, and acknowledgements", () => {
    const expected = stored();
    const memory = new MemoryGraphStore();
    memory.save(sample());
    expect(memory.load()).toEqual(expected);

    const second = new MemoryGraphStore();
    second.replace(memory.snapshot());
    memory.save({ events: [], advertisements: [], nodes: [], acknowledgements: [] });
    expect(second.load()).toEqual(expected);

    const storage = new MapStorage();
    const browser = new BrowserGraphStore(storage);
    expect(browser.load()).toEqual({
      events: [],
      advertisements: [],
      nodes: [],
      acknowledgements: [],
    });
    browser.save(sample());
    browser.save(expected);
    expect(browser.load()).toEqual(expected);
    const raw = storage.getItem(GRAPH_STORE_KEY);
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw ?? "") as DurableSnapshot & { sessions?: unknown };
    expect(Object.keys(parsed).sort()).toEqual([
      "acknowledgements",
      "advertisements",
      "events",
      "nodes",
    ]);
    expect(parsed.sessions).toBeUndefined();
  });

  it("stores acknowledgement endpoint ids in canonical order", () => {
    const input = sample();
    const memory = new MemoryGraphStore();
    memory.save(input);
    expect(input.acknowledgements[0]?.endpointIds).toEqual(["b", "a"]);
    expect(memory.snapshot().acknowledgements[0]?.endpointIds).toEqual(["a", "b"]);

    const storage = new MapStorage();
    const browser = new BrowserGraphStore(storage);
    browser.save(sample());
    const parsed = JSON.parse(storage.getItem(GRAPH_STORE_KEY) ?? "") as DurableSnapshot;
    expect(parsed.acknowledgements[0]?.endpointIds).toEqual(["a", "b"]);
    expect(browser.load().acknowledgements[0]?.endpointIds).toEqual(["a", "b"]);
  });

  it("clears sessions without changing the graph snapshot", () => {
    const memory = new MemoryGraphStore();
    memory.save(sample());
    const before = memory.snapshot();
    const sessions = new MemorySessionStore();
    sessions.put("rh_abc", { personId: "p1", purpose: "look", session: "exploration" });
    expect(sessions.get("rh_missing")).toBeUndefined();
    sessions.delete("rh_abc");
    expect(sessions.get("rh_abc")).toBeUndefined();
    sessions.put("rh_abc", { personId: "p1", purpose: "look" });
    sessions.clear();
    expect(sessions.get("rh_abc")).toBeUndefined();
    expect(memory.snapshot()).toEqual(before);
    expect(memory.load()).toEqual(stored());
  });

  it("throws when the browser payload is corrupt and does not return a partial graph", () => {
    const storage = new MapStorage();
    const browser = new BrowserGraphStore(storage);
    storage.setItem(GRAPH_STORE_KEY, "{");
    let loaded: DurableSnapshot | undefined;
    expect(() => {
      loaded = browser.load();
    }).toThrow("graph store snapshot is unreadable");
    expect(loaded).toBeUndefined();

    storage.setItem(
      GRAPH_STORE_KEY,
      JSON.stringify({ events: sample().events, advertisements: [] }),
    );
    expect(() => browser.load()).toThrow("graph store snapshot is unreadable");
  });
});
