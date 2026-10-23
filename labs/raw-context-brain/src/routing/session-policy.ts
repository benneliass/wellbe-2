/**
 * Pure exploration-session policy for one pinned walk.
 * A null terminal and supported_leaf keep the session inspectable and rewindable.
 * policy_blocked, authorization_changed, stale_snapshot, and dependency_unavailable release it.
 * budget_exhausted and insufficient_independent_evidence release it: the design leaves them closed.
 * approximate_frontier_exhausted releases it.
 * Rewind cuts an on-path node to the tip. Forward items are frontier rows expanded from that tip.
 * Open advertisements stay at three. Issued actions stay within seven and keep a fallback when one was present.
 */

/** Local copy of the lab terminal union. This module stays free of other lab imports. */
export type TerminalReason =
  | "supported_leaf"
  | "approximate_frontier_exhausted"
  | "budget_exhausted"
  | "policy_blocked"
  | "authorization_changed"
  | "stale_snapshot"
  | "dependency_unavailable"
  | "insufficient_independent_evidence";

export type TruncatePathResult = { visited: string[] } | { error: "rewind_target" };

export interface FrontierRef {
  nodeId: string;
  fromId: string;
}

export type IssuedKind = "neighbour" | "facet" | "temporal" | "source" | "fallback";

export interface IssuedAction {
  kind: IssuedKind;
}

const OPEN_NODE_CAP = 3;
const ISSUED_TOTAL_CAP = 7;

/**
 * True while the session stays inspectable.
 * supported_leaf has no eligible forward node and remains rewindable.
 * A null terminal means the walk can continue.
 */
export function retainsSession(terminal: TerminalReason | null): boolean {
  switch (terminal) {
    case null:
    case "supported_leaf":
      return true;
    case "approximate_frontier_exhausted":
    case "budget_exhausted":
    case "policy_blocked":
    case "authorization_changed":
    case "stale_snapshot":
    case "dependency_unavailable":
    case "insufficient_independent_evidence":
      return false;
  }
}

/**
 * Cuts visited so targetId is the new tip.
 * A target that is already the tip returns the same path.
 * A target absent from the path returns rewind_target and leaves the input path unchanged.
 */
export function truncatePath(visited: string[], targetId: string): TruncatePathResult {
  const tipIndex = visited.length - 1;
  if (tipIndex >= 0 && visited[tipIndex] === targetId) {
    return { visited: visited.slice() };
  }
  const index = visited.indexOf(targetId);
  if (index < 0) return { error: "rewind_target" };
  return { visited: visited.slice(0, index + 1) };
}

/** Frontier rows whose fromId is the current tip. Earlier expansions stay off the forward set. */
export function forwardItems<T extends FrontierRef>(items: readonly T[], tipId: string): T[] {
  return items.filter((item) => item.fromId === tipId);
}

/** Open-node advertisements, clamped to at most three. */
export function boundForwardActions(count: number): number {
  if (!Number.isFinite(count) || count < 1) return 0;
  return Math.min(OPEN_NODE_CAP, Math.floor(count));
}

/**
 * The same list, limited to three neighbour actions and seven actions in total.
 * When a fallback is present it stays in the result.
 * With enough candidates the issued length sits between three and seven.
 */
export function selectIssuedActions<T extends IssuedAction>(actions: readonly T[]): T[] {
  const openBudget = boundForwardActions(actions.filter((action) => action.kind === "neighbour").length);
  const fallbackAt = actions.findIndex((action) => action.kind === "fallback");
  const selected: T[] = [];
  let opens = 0;

  for (let index = 0; index < actions.length; index += 1) {
    const action = actions[index];
    if (!action) continue;
    if (action.kind === "neighbour" && opens >= openBudget) continue;
    const reserveFallback = fallbackAt > index;
    const limit = reserveFallback ? ISSUED_TOTAL_CAP - 1 : ISSUED_TOTAL_CAP;
    if (selected.length >= limit) continue;
    if (action.kind === "neighbour") opens += 1;
    selected.push(action);
  }

  return selected;
}
