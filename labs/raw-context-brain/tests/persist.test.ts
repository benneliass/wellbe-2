import { describe, expect, it } from "vitest";
import {
  PostgresPointerStore,
  SCHEMA_SQL,
  WALK_SQL,
  replay,
  type Queryable,
} from "../src/persist/postgres-store.js";
import { AdvertisementLog, Projection, type AdvertisementDraft } from "../src/store.js";
import type { LinkAdvertisement, VaultEvent } from "../src/types.js";

class FakeDb implements Queryable {
  events = new Map<string, unknown[]>();
  ads: unknown[][] = [];
  edges = new Map<string, unknown[]>();
  queries: string[] = [];

  async query<T>(sql: string, params: unknown[] = []): Promise<{ rows: T[] }> {
    this.queries.push(sql);
    if (sql.startsWith("SELECT id FROM rcb_vault_event")) {
      const row = this.events.get(String(params[0]));
      return { rows: row ? [{ id: params[0] } as T] : [] };
    }
    if (sql.startsWith("INSERT INTO rcb_vault_event")) {
      this.events.set(String(params[0]), params);
      return { rows: [] };
    }
    if (sql.includes("MAX(sequence)")) {
      const max = this.ads.reduce((best, row) => Math.max(best, Number(row[1])), 0);
      return { rows: [{ max_sequence: max } as T] };
    }
    if (sql.startsWith("INSERT INTO rcb_link_advertisement")) {
      this.ads.push(params);
      return { rows: [] };
    }
    if (sql.startsWith("DELETE FROM rcb_pointer_edge")) {
      const person = String(params[0]);
      const a = String(params[1]);
      const b = String(params[2]);
      this.edges.delete(`${person}|${a}|${b}`);
      this.edges.delete(`${person}|${b}|${a}`);
      return { rows: [] };
    }
    if (sql.startsWith("INSERT INTO rcb_pointer_edge")) {
      this.edges.set(`${params[0]}|${params[1]}|${params[2]}`, params);
      return { rows: [] };
    }
    if (sql.startsWith("SELECT dst_id")) {
      const person = String(params[0]);
      const srcs = new Set(params[1] as string[]);
      const rows = [...this.edges.entries()]
        .filter(([key]) => key.startsWith(`${person}|`) && srcs.has(key.split("|")[1] ?? ""))
        .map(([, row]) => ({ dst_id: row[2] }))
        .sort((left, right) => String(left.dst_id).localeCompare(String(right.dst_id)));
      return { rows: rows as T[] };
    }
    if (sql === WALK_SQL) {
      expect(params[2]).toBeTypeOf("number");
      return { rows: [] };
    }
    throw new Error(`unexpected sql: ${sql}`);
  }
}

function event(): VaultEvent {
  return {
    id: "n1",
    personId: "p1",
    capturedAt: "2024-01-01",
    sourceType: "note",
    text: "short sleep",
    contentHash: "h",
    lineageId: "sleep",
    documentId: null,
  };
}

function draft(partial: Partial<AdvertisementDraft>): AdvertisementDraft {
  return {
    personId: "p1",
    origin: "model",
    modelVersion: "lab",
    promptVersion: null,
    policyVersion: "lab-policy-1",
    evidenceIds: ["n1", "n2"],
    fromId: "n1",
    toId: "n2",
    judgment: "link",
    reasonCode: "shared_context",
    relation: "possible_semantic_association",
    proposedConfidence: 0.4,
    confidence: 0.4,
    createdAt: "2024-01-02",
    supersedesId: null,
    withdrawn: false,
    ...partial,
  };
}

describe("postgres pointer store", () => {
  it("keeps vault text off the edge table and bounds the walk", () => {
    const edge = SCHEMA_SQL.split("CREATE TABLE rcb_pointer_edge")[1]?.split("CREATE INDEX")[0] ?? "";
    expect(edge).not.toContain("note_text");
    expect(SCHEMA_SQL).toContain("CREATE INDEX rcb_pointer_edge_src ON rcb_pointer_edge (person_id, src_id)");
    expect(WALK_SQL).toContain("w.depth < $3");
    expect(WALK_SQL).toContain("ANY(w.path)");
  });

  it("refuses a second write of the same vault id", async () => {
    const store = new PostgresPointerStore(new FakeDb());
    await store.appendEvent(event());
    await expect(store.appendEvent(event())).rejects.toThrow("vault is append-only");
  });

  it("leaves an accepted edge in place when a later model judgment abstains", async () => {
    const db = new FakeDb();
    const store = new PostgresPointerStore(db);
    await store.appendAdvertisement("p1", draft({}));
    await store.appendAdvertisement("p1", draft({ judgment: "uncertain", confidence: 0.1 }));
    await store.appendAdvertisement("p1", draft({ judgment: "no_link", confidence: 0.1 }));
    expect(await store.neighbors("p1", ["n1"])).toEqual(["n2"]);
    await store.appendAdvertisement("p1", draft({ withdrawn: true }));
    expect(await store.neighbors("p1", ["n1"])).toEqual([]);
  });

  it("replays advertisements to the same digest as the in-memory projection", () => {
    const log = new AdvertisementLog();
    const ads: LinkAdvertisement[] = [
      log.append(draft({})),
      log.append(draft({ judgment: "no_link", confidence: 0.1 })),
    ];
    const live = new Projection();
    for (const ad of ads) live.apply(ad);
    expect(replay(ads).digest).toBe(live.digest);
  });
});
