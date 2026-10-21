/**
 * Privacy gate for the lab's hosted judge.
 * The individual confirms the provider agreement and retention.
 * No other flag turns the hosted judge on. This module does not call the network.
 */

export type ReadinessEnv = NodeJS.ProcessEnv | null | undefined;

/** Live model column. A heuristic percentage is never attached. */
export type ModelColumn = { column: "not_run" } | { column: "model" };

export type FounderColumn =
  | { column: "founder"; pairs: readonly unknown[] }
  | { column: "heuristic" };

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
const LONG_DIGIT_RUN = /[0-9]{9,}/;

export function hostedJudgeAllowed(env: ReadinessEnv): boolean {
  if (env == null) return false;
  return env.WELLBE_PROVIDER_AGREEMENT === "on" && env.WELLBE_RETENTION_CONFIRMED === "on";
}

export function modelColumn(env: ReadinessEnv): ModelColumn {
  const apiKey = env?.OPENAI_API_KEY;
  const keyPresent = typeof apiKey === "string" && apiKey.trim().length > 0;
  if (!hostedJudgeAllowed(env) || !keyPresent) return { column: "not_run" };
  return { column: "model" };
}

export function loadFounderGold(parsed: unknown): FounderColumn {
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { column: "heuristic" };
  }
  const record = parsed as Record<string, unknown>;
  const reviewer = record.reviewer;
  if (
    record.reviewed !== true ||
    typeof reviewer !== "string" ||
    reviewer.trim().length === 0 ||
    !Array.isArray(record.pairs)
  ) {
    return { column: "heuristic" };
  }
  return { column: "founder", pairs: record.pairs };
}

export function assertLabNote(text: string, env: ReadinessEnv): void {
  if (hostedJudgeAllowed(env)) return;
  if (EMAIL.test(text) || LONG_DIGIT_RUN.test(text)) {
    throw new Error("real_note_blocked");
  }
}
