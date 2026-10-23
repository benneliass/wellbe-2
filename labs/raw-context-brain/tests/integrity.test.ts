import { describe, expect, it } from "vitest";
import { assertAdvertisementDigests, rowHash, type RowHashInput } from "../src/integrity/row-hash.js";
import { assertStructuralLedger } from "../src/integrity/structural.js";
import { AdvertisementLog, Projection, type AdvertisementDraft } from "../src/store.js";
import type { LinkAdvertisement } from "../src/types.js";

function row(partial: Partial<RowHashInput> = {}): RowHashInput {
  return {
    personId: "p1",
    sequence: 1,
    origin: "model",
    modelVersion: "lab",
    promptVersion: "lab-prompt-1",
    policyVersion: "lab-policy-1",
    evidenceIds: ["n2", "n1"],
    fromId: "n1",
    toId: "n2",
    judgment: "link",
    reasonCode: "shared_context",
    relation: "possible_semantic_association",
    proposedConfidence: 0.4,
    confidence: 0.4,
    createdAt: "2024-01-02T00:00:00.000Z",
    supersedesId: null,
    withdrawn: false,
    ...partial,
  };
}

function draft(partial: Partial<AdvertisementDraft> = {}): AdvertisementDraft {
  const { sequence: _sequence, ...fields } = row();
  return { ...fields, ...partial };
}

function structuralAd(partial: Partial<RowHashInput> & { id: string }): LinkAdvertisement {
  const { id, ...fields } = partial;
  const complete = row({
    origin: "policy",
    modelVersion: null,
    promptVersion: null,
    reasonCode: "membership",
    relation: "same_record_group",
    evidenceIds: [],
    ...fields,
  });
  return { ...complete, id, digest: rowHash(complete) };
}

const hub = { id: "hub-1", kind: "pseudonode", memberEventIds: ["evt-1"] };
const member = { id: "evt-1", kind: "event", memberEventIds: [] as string[] };

describe("ledger row hash", () => {
  it("changes when a previously uncovered field changes", () => {
    const base = rowHash(row());
    expect(rowHash(row({ modelVersion: "lab-2" }))).not.toBe(base);
    expect(rowHash(row({ promptVersion: "lab-prompt-2" }))).not.toBe(base);
    expect(rowHash(row({ policyVersion: "lab-policy-2" }))).not.toBe(base);
    expect(rowHash(row({ proposedConfidence: 0.9 }))).not.toBe(base);
    expect(rowHash(row({ createdAt: "2024-03-03T00:00:00.000Z" }))).not.toBe(base);
    expect(rowHash(row({ evidenceIds: ["n1", "n2"] }))).toBe(base);
    const stored = { ...row(), id: "ad-1", digest: "not-part-of-the-row" };
    expect(rowHash(stored)).toBe(base);
  });

  it("throws on a tampered digest and does not publish that edge", () => {
    const log = new AdvertisementLog();
    const ad = log.append(draft());
    log.verifyDigests();

    const projection = new Projection();
    projection.rebuild([ad]);
    expect(projection.edgeBetween(ad.fromId, ad.toId)?.adId).toBe(ad.id);

    const tampered: LinkAdvertisement = {
      ...ad,
      id: "ad-tampered",
      confidence: 0.99,
      digest: "tampered",
    };
    expect(() => assertAdvertisementDigests([tampered])).toThrow(
      "advertisement digest mismatch at ad-tampered",
    );
    expect(() => projection.rebuild([tampered])).toThrow(
      "advertisement digest mismatch at ad-tampered",
    );
    expect(projection.edgeBetween(ad.fromId, ad.toId)).toMatchObject({
      adId: ad.id,
      confidence: ad.confidence,
    });
    expect(projection.status).toBe("ready");

    log.ads.push(tampered);
    expect(() => log.verifyDigests()).toThrow("advertisement digest mismatch at ad-tampered");
  });
});

describe("structural ledger", () => {
  it("accepts a hub and a member in that hub", () => {
    const ads = [structuralAd({ id: "ad-1", fromId: "evt-1", toId: "hub-1" })];
    expect(() => assertStructuralLedger(ads, [hub, member])).not.toThrow();
  });

  it("rejects a hub link whose other end is not a member", () => {
    const ads = [structuralAd({ id: "ad-1", fromId: "evt-9", toId: "hub-1" })];
    const nodes = [hub, { id: "evt-9", kind: "event", memberEventIds: [] }];
    expect(() => assertStructuralLedger(ads, nodes)).toThrow(
      "structural link ad-1 does not match source-group membership",
    );
  });

  it("rejects same_record_group between two event nodes", () => {
    const ads = [structuralAd({ id: "ad-1", fromId: "evt-1", toId: "evt-2" })];
    const nodes = [
      member,
      { id: "evt-2", kind: "event", memberEventIds: [] },
    ];
    expect(() => assertStructuralLedger(ads, nodes)).toThrow(
      "structural link ad-1 does not match source-group membership",
    );
  });

  it("rejects a hub member with no policy ledger row", () => {
    expect(() => assertStructuralLedger([], [hub])).toThrow(
      "structural membership evt-1 has no policy ledger row",
    );
  });

  it("does not treat a withdrawn hub link as the required policy row", () => {
    const ads = [structuralAd({ id: "ad-1", fromId: "evt-1", toId: "hub-1", withdrawn: true })];
    expect(() => assertStructuralLedger(ads, [hub, member])).toThrow(
      "structural membership evt-1 has no policy ledger row",
    );
  });
});
