/**
 * When to wait and when to stop. This module does not sleep.
 * Deadline, in-flight cap, and the attempt limit share the terminal reason
 * dependency_unavailable. The caller waits delayMs, then asks again.
 */

export interface AttemptInput {
  attempt: number;
  now: number;
  startedAt: number;
  deadlineMs: number;
  baseMs: number;
  inFlight: number;
  maxInFlight: number;
  seed: number;
}

export type AttemptDecision =
  | { action: "stop"; reason: "dependency_unavailable" }
  | { action: "wait"; delayMs: number };

const ATTEMPT_LIMIT = 3;

export function scheduleAttempt(input: AttemptInput): AttemptDecision {
  if (input.now > input.startedAt + input.deadlineMs) return stop();
  if (input.inFlight >= input.maxInFlight) return stop();
  if (input.attempt >= ATTEMPT_LIMIT) return stop();
  const delayMs = input.baseMs * 2 ** input.attempt + ((input.seed + input.attempt) % 3);
  return { action: "wait", delayMs };
}

function stop(): AttemptDecision {
  return { action: "stop", reason: "dependency_unavailable" };
}
