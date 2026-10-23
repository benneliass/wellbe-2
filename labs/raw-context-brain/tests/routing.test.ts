import { describe, expect, it } from "vitest";
import { createPendingInterestTable, type SemanticInterest } from "../src/routing/interest.js";
import { createRouteSets, type RouteProvenance } from "../src/routing/route-sets.js";
import { applyReferralRound, applySelection, type RankedCandidate } from "../src/routing/selection.js";
import { scheduleAttempt, type AttemptInput } from "../src/routing/retry.js";

const PERSON = "person-1";

function provenance(
  discovery: RouteProvenance["discovery"],
  rank: number,
  pruneReason: string | null,
  exportHandle: string | null = null,
): RouteProvenance {
  return { discovery, rank, pruneReason, exportHandle };
}

function interest(overrides: Partial<SemanticInterest> = {}): SemanticInterest {
  return {
    personId: PERSON,
    purpose: "inspect",
    authorizationEpoch: 1,
    snapshotRevision: 4,
    snapshotDigest: "digest-a",
    budgets: { deadlineMs: 50, maxInFlight: 2 },
    operation: "open",
    nonce: "nonce-1",
    ...overrides,
  };
}

function candidate(overrides: Partial<RankedCandidate> & Pick<RankedCandidate, "id">): RankedCandidate {
  return {
    lineage: overrides.id,
    sourceType: overrides.id,
    facet: overrides.id,
    reason: overrides.id,
    capturedAt: "2024-06-01",
    relevance: 0,
    neighbors: [],
    ...overrides,
  };
}

describe("route set revisions", () => {
  it("appends revisions and keeps the earlier publication", () => {
    const log = createRouteSets();
    const first = log.publish({
      personId: PERSON,
      sets: {
        candidate: ["a", "b", "c", "e"],
        selected: ["a", "b"],
        export: ["a"],
      },
      provenance: {
        a: provenance("exact", 0, null, "rh_a"),
        b: provenance("neighbor", 1, null),
        e: provenance("exact", 2, "lineage_cap"),
        c: provenance("hnsw", 3, "facet_cap"),
      },
    });

    expect(first.revision).toBe(1);
    expect(first.transitions).toEqual([
      { revision: 1, from: "candidate", to: "selected", entered: ["a", "b"], left: [] },
      { revision: 1, from: "selected", to: "export", entered: ["a"], left: [] },
    ]);
    expect(log.pruneAudit(1)).toEqual([
      { id: "e", reason: "lineage_cap" },
      { id: "c", reason: "facet_cap" },
    ]);

    const second = log.publish({
      personId: PERSON,
      sets: {
        candidate: ["a", "d"],
        selected: ["d"],
        export: ["d"],
      },
      provenance: {
        a: provenance("exact", 1, "reason_cap"),
        d: provenance("referral", 0, null, "rh_d"),
      },
    });

    expect(second.revision).toBe(2);
    expect(second.transitions).toEqual([
      { revision: 2, from: "candidate", to: "selected", entered: ["d"], left: ["a", "b"] },
      { revision: 2, from: "selected", to: "export", entered: ["d"], left: ["a"] },
    ]);
    expect(log.history(PERSON).map((row) => row.revision)).toEqual([1, 2]);
    expect(log.history(PERSON)[0]).toEqual(first);
    expect(log.latest(PERSON)).toEqual(second);
    expect(log.pruneAudit(2)).toEqual([{ id: "a", reason: "reason_cap" }]);

    const third = log.publish({
      personId: PERSON,
      sets: second.sets,
      provenance: second.provenance,
    });
    expect(third.revision).toBe(3);
    expect(third.transitions).toEqual([
      { revision: 3, from: "candidate", to: "selected", entered: [], left: [] },
      { revision: 3, from: "selected", to: "export", entered: [], left: [] },
    ]);
    expect(log.history(PERSON)[1]).toEqual(second);
    expect(log.latest(PERSON)?.revision).toBe(3);

    const other = log.publish({
      personId: "person-2",
      sets: { candidate: ["x"], selected: ["x"], export: [] },
      provenance: { x: provenance("exact", 0, null) },
    });
    expect(other.transitions[0]).toEqual({
      revision: other.revision,
      from: "candidate",
      to: "selected",
      entered: ["x"],
      left: [],
    });
    expect(log.history(PERSON)).toHaveLength(3);
    expect(log.latest("person-2")?.sets.candidate).toEqual(["x"]);
    expect(log.history("person-2")).toHaveLength(1);
  });
});

describe("pending interest", () => {
  it("coalesces equivalent work, replays a nonce, and rejects a different purpose", async () => {
    const table = createPendingInterestTable();
    const first = interest();
    const opened = table.begin(first, "anchor-a");
    expect(opened).toMatchObject({ state: "pending", nonce: "nonce-1", joined: false });

    const joined = table.begin(interest({ nonce: "nonce-2" }), "anchor-a");
    expect(joined).toMatchObject({ state: "pending", nonce: "nonce-1", joined: true });
    if (opened.state !== "pending" || joined.state !== "pending") throw new Error("expected pending");
    expect(joined.done).toBe(opened.done);

    const otherSnapshot = table.begin(interest({ nonce: "nonce-3", snapshotRevision: 9 }), "anchor-a");
    expect(otherSnapshot).toMatchObject({ state: "pending", nonce: "nonce-3", joined: false });

    expect(table.begin(interest({ purpose: "share" }), "anchor-a")).toEqual({
      state: "rejected",
      reason: "wrong_purpose",
    });
    expect(table.begin(first, "anchor-a")).toMatchObject({ state: "pending", nonce: "nonce-1", joined: false });

    table.satisfy("nonce-1", { page: 1 });
    await expect(opened.done).resolves.toEqual({ page: 1 });
    table.satisfy("nonce-1", { page: 2 });

    expect(table.begin(first, "other-key")).toEqual({
      state: "satisfied",
      nonce: "nonce-1",
      result: { page: 1 },
    });

    const again = table.begin(interest({ nonce: "nonce-4" }), "anchor-a");
    expect(again).toMatchObject({ state: "pending", nonce: "nonce-4", joined: false });

    table.clear();
    expect(table.begin(first, "anchor-a")).toMatchObject({ state: "pending", nonce: "nonce-1", joined: false });
  });
});

describe("selection caps", () => {
  it("reserves one earlier and one later and caps a facet at two", () => {
    const result = applySelection({
      capturedAt: "2024-06-01",
      candidates: [
        candidate({
          id: "same-1",
          lineage: "l1",
          sourceType: "note",
          facet: "sleep",
          reason: "r1",
          relevance: 0.9,
        }),
        candidate({
          id: "same-2",
          lineage: "l2",
          sourceType: "lab",
          facet: "sleep",
          reason: "r2",
          relevance: 0.8,
          neighbors: [
            { id: "closer-a", relevance: 0.95 },
            { id: "weaker", relevance: 0.2 },
          ],
        }),
        candidate({
          id: "earlier",
          lineage: "l3",
          sourceType: "pdf",
          facet: "sleep",
          reason: "r3",
          capturedAt: "2024-01-01",
          relevance: 0.5,
        }),
        candidate({
          id: "later",
          lineage: "l4",
          sourceType: "image",
          facet: "knee",
          reason: "r4",
          capturedAt: "2024-08-01",
          relevance: 0.45,
        }),
        candidate({
          id: "fourth-sleep",
          lineage: "l5",
          sourceType: "letter",
          facet: "sleep",
          reason: "r5",
          capturedAt: "2024-03-01",
          relevance: 0.3,
          neighbors: [{ id: "closer-b", relevance: 0.7 }],
        }),
      ],
    });

    expect(result.kept).toEqual(["earlier", "later", "same-1"]);
    expect(result.pruned).toEqual([
      { id: "same-2", reason: "facet_cap" },
      { id: "fourth-sleep", reason: "facet_cap" },
    ]);
    expect(result.referrals).toEqual(["closer-a", "closer-b"]);
  });
});

describe("referral round", () => {
  it("proposes one round of closer neighbors after a no_link", () => {
    expect(
      applyReferralRound({
        judged: [
          {
            id: "a",
            judgment: "no_link",
            relevance: 0.4,
            neighbors: [
              { id: "seen", relevance: 0.95 },
              { id: "b", relevance: 0.7 },
              { id: "low", relevance: 0.4 },
              { id: "c", relevance: 0.8 },
              { id: "d", relevance: 0.9 },
            ],
          },
          {
            id: "linked",
            judgment: "link",
            relevance: 0.1,
            neighbors: [{ id: "not-proposed", relevance: 1 }],
          },
        ],
        tried: ["a", "linked", "seen"],
      }).referrals,
    ).toEqual(["b", "c"]);

    expect(
      applyReferralRound({
        judged: [
          {
            id: "u",
            judgment: "uncertain",
            relevance: 0.2,
            neighbors: [
              { id: "n", relevance: 0.5 },
              { id: "m", relevance: 0.4 },
            ],
          },
        ],
        tried: ["u"],
      }).referrals,
    ).toEqual(["n", "m"]);
  });
});

describe("retry schedule", () => {
  const base: AttemptInput = {
    attempt: 0,
    now: 1_000,
    startedAt: 1_000,
    deadlineMs: 50,
    baseMs: 10,
    inFlight: 0,
    maxInFlight: 2,
    seed: 4,
  };

  it("stops on the deadline and on overload", () => {
    expect(scheduleAttempt({ ...base, now: 1_050 })).toEqual({ action: "wait", delayMs: 11 });
    expect(scheduleAttempt({ ...base, now: 1_051 })).toEqual({
      action: "stop",
      reason: "dependency_unavailable",
    });
    expect(scheduleAttempt({ ...base, inFlight: 2 })).toEqual({
      action: "stop",
      reason: "dependency_unavailable",
    });
    expect(scheduleAttempt({ ...base, attempt: 1 })).toEqual({ action: "wait", delayMs: 22 });
    expect(scheduleAttempt({ ...base, attempt: 2 })).toEqual({ action: "wait", delayMs: 40 });
    expect(scheduleAttempt({ ...base, attempt: 3 })).toEqual({
      action: "stop",
      reason: "dependency_unavailable",
    });
  });
});
