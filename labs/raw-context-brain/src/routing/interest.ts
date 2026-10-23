/**
 * Temporary pending-interest state for one person.
 * Equivalent in-flight requests share one nonce. The same nonce replays one saved result.
 * A joined caller keeps the in-flight nonce. Its own nonce is not recorded.
 * clear drops the session. Nothing here is graph topology.
 */

export interface InterestBudgets {
  deadlineMs: number;
  maxInFlight: number;
}

export interface SemanticInterest {
  personId: string;
  purpose: string;
  authorizationEpoch: number;
  snapshotRevision: number;
  snapshotDigest: string;
  budgets: InterestBudgets;
  operation: string;
  nonce: string;
}

export interface PendingBegin {
  state: "pending";
  nonce: string;
  joined: boolean;
  /** Shared slot. The first satisfy resolves it once. */
  done: Promise<unknown>;
}

export interface SatisfiedBegin {
  state: "satisfied";
  nonce: string;
  result: unknown;
}

export interface RejectedBegin {
  state: "rejected";
  reason: "wrong_purpose";
}

export type BeginResult = PendingBegin | SatisfiedBegin | RejectedBegin;

export interface PendingInterestTable {
  begin(interest: SemanticInterest, workKey: string): BeginResult;
  satisfy(nonce: string, result: unknown): void;
  clear(): void;
}

interface Deferred {
  promise: Promise<unknown>;
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}

interface Slot {
  interest: SemanticInterest;
  state: "pending" | "satisfied";
  result?: unknown;
  deferred: Deferred;
}

export function createPendingInterestTable(): PendingInterestTable {
  const byNonce = new Map<string, Slot>();
  const byJoin = new Map<string, string>();

  return {
    begin(interest, workKey) {
      const known = byNonce.get(interest.nonce);
      if (known) {
        if (known.interest.purpose !== interest.purpose) return { state: "rejected", reason: "wrong_purpose" };
        if (known.state === "satisfied") {
          return { state: "satisfied", nonce: known.interest.nonce, result: known.result };
        }
        return pendingBegin(known, false);
      }

      const key = joinKey(interest, workKey);
      const inFlightNonce = byJoin.get(key);
      const inFlight = inFlightNonce ? byNonce.get(inFlightNonce) : undefined;
      if (inFlight && inFlight.state === "pending") return pendingBegin(inFlight, true);

      const slot: Slot = { interest: copyInterest(interest), state: "pending", deferred: defer() };
      byNonce.set(interest.nonce, slot);
      byJoin.set(key, interest.nonce);
      return pendingBegin(slot, false);
    },

    satisfy(nonce, result) {
      const slot = byNonce.get(nonce);
      if (!slot || slot.state === "satisfied") return;
      slot.state = "satisfied";
      slot.result = result;
      slot.deferred.resolve(result);
    },

    clear() {
      for (const slot of byNonce.values()) {
        if (slot.state !== "pending") continue;
        slot.deferred.promise.catch(() => undefined);
        slot.deferred.reject(new Error("session_expired"));
      }
      byNonce.clear();
      byJoin.clear();
    },
  };
}

function pendingBegin(slot: Slot, joined: boolean): PendingBegin {
  return { state: "pending", nonce: slot.interest.nonce, joined, done: slot.deferred.promise };
}

/** Nonce is a request id, not part of equivalence. */
function joinKey(interest: SemanticInterest, workKey: string): string {
  return JSON.stringify([
    interest.personId,
    interest.purpose,
    interest.operation,
    interest.snapshotRevision,
    workKey,
  ]);
}

function copyInterest(interest: SemanticInterest): SemanticInterest {
  return {
    ...interest,
    budgets: { ...interest.budgets },
  };
}

function defer(): Deferred {
  let resolve: (value: unknown) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<unknown>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
