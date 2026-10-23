/**
 * Three policy route sets for one person: candidate, selected, and export.
 * These are policy objects, not Links and not a network protocol.
 * Each publication appends a revision. A revision is never overwritten.
 * Revision numbers belong to this log. They are never reused.
 * Nothing here joins one person's ids with another person's ids.
 */

export const ROUTE_SET_NAMES = ["candidate", "selected", "export"] as const;

export type RouteSetName = (typeof ROUTE_SET_NAMES)[number];

export const DISCOVERY_SOURCES = ["exact", "neighbor", "hnsw", "referral"] as const;

export type DiscoverySource = (typeof DISCOVERY_SOURCES)[number];

/** Per-id derivation recorded with the revision that published it. */
export interface RouteProvenance {
  discovery: DiscoverySource;
  rank: number;
  pruneReason: string | null;
  exportHandle: string | null;
}

export interface RouteSetsSnapshot {
  candidate: readonly string[];
  selected: readonly string[];
  export: readonly string[];
}

/**
 * One hop in this revision.
 * entered and left are ids that entered or left the destination set
 * since the previous revision for this person. The first revision
 * compares with an empty destination.
 */
export interface RouteTransition {
  revision: number;
  from: RouteSetName;
  to: RouteSetName;
  entered: readonly string[];
  left: readonly string[];
}

export interface RouteRevision {
  personId: string;
  revision: number;
  sets: RouteSetsSnapshot;
  provenance: Readonly<Record<string, RouteProvenance>>;
  transitions: readonly RouteTransition[];
}

export interface RoutePublication {
  personId: string;
  sets: RouteSetsSnapshot;
  provenance: Readonly<Record<string, RouteProvenance>>;
}

export interface PruneAuditRow {
  id: string;
  reason: string;
}

export interface RouteSetLog {
  publish(publication: RoutePublication): RouteRevision;
  latest(personId: string): RouteRevision | undefined;
  history(personId: string): readonly RouteRevision[];
  pruneAudit(revision: number): PruneAuditRow[];
}

const HOPS: readonly (readonly [RouteSetName, RouteSetName])[] = [
  ["candidate", "selected"],
  ["selected", "export"],
];

const EMPTY_SETS: RouteSetsSnapshot = { candidate: [], selected: [], export: [] };

export function createRouteSets(): RouteSetLog {
  const byPerson = new Map<string, RouteRevision[]>();
  const byRevision = new Map<number, RouteRevision>();
  let nextRevision = 1;

  return {
    publish(publication) {
      const revision = nextRevision;
      nextRevision += 1;
      const previous = byPerson.get(publication.personId)?.at(-1);
      const stored: RouteRevision = {
        personId: publication.personId,
        revision,
        sets: copySets(publication.sets),
        provenance: copyProvenance(publication.provenance),
        transitions: transitionsFor(revision, previous?.sets, publication.sets),
      };
      const history = byPerson.get(publication.personId) ?? [];
      history.push(stored);
      byPerson.set(publication.personId, history);
      byRevision.set(revision, stored);
      return copyRevision(stored);
    },

    latest(personId) {
      const current = byPerson.get(personId)?.at(-1);
      return current ? copyRevision(current) : undefined;
    },

    history(personId) {
      return (byPerson.get(personId) ?? []).map(copyRevision);
    },

    pruneAudit(revision) {
      const found = byRevision.get(revision);
      if (!found) return [];
      return Object.entries(found.provenance)
        .filter((entry): entry is [string, RouteProvenance & { pruneReason: string }] => entry[1].pruneReason !== null)
        .sort(byRank)
        .map(([id, row]) => ({ id, reason: row.pruneReason }));
    },
  };
}

function transitionsFor(
  revision: number,
  previous: RouteSetsSnapshot | undefined,
  next: RouteSetsSnapshot,
): RouteTransition[] {
  const before = previous ?? EMPTY_SETS;
  return HOPS.map(([from, to]) => {
    const change = membershipChange(before[to], next[to]);
    return { revision, from, to, entered: change.entered, left: change.left };
  });
}

function membershipChange(
  before: readonly string[],
  after: readonly string[],
): { entered: string[]; left: string[] } {
  const prior = new Set(before);
  const next = new Set(after);
  return {
    entered: after.filter((id) => !prior.has(id)),
    left: before.filter((id) => !next.has(id)),
  };
}

function byRank(
  left: [string, RouteProvenance],
  right: [string, RouteProvenance],
): number {
  if (left[1].rank !== right[1].rank) return left[1].rank - right[1].rank;
  if (left[0] === right[0]) return 0;
  return left[0] < right[0] ? -1 : 1;
}

function copySets(sets: RouteSetsSnapshot): RouteSetsSnapshot {
  return {
    candidate: [...sets.candidate],
    selected: [...sets.selected],
    export: [...sets.export],
  };
}

function copyProvenance(
  provenance: Readonly<Record<string, RouteProvenance>>,
): Record<string, RouteProvenance> {
  const copy: Record<string, RouteProvenance> = {};
  for (const [id, row] of Object.entries(provenance)) copy[id] = { ...row };
  return copy;
}

function copyRevision(revision: RouteRevision): RouteRevision {
  return {
    personId: revision.personId,
    revision: revision.revision,
    sets: copySets(revision.sets),
    provenance: copyProvenance(revision.provenance),
    transitions: revision.transitions.map((transition) => ({
      revision: transition.revision,
      from: transition.from,
      to: transition.to,
      entered: [...transition.entered],
      left: [...transition.left],
    })),
  };
}
