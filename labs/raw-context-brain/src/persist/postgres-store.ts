import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Projection, type AdvertisementDraft } from "../store.js";
import { sha256 } from "../text.js";
import type { LinkAdvertisement, VaultEvent } from "../types.js";

export const SCHEMA_SQL = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "schema.sql"),
  "utf8",
);

export interface Queryable {
  query<T = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
}

/** Neighbors of the given ids for one person. Depth is $3. The path stops a cycle. */
export const WALK_SQL = `
WITH RECURSIVE walk AS (
  SELECT src_id, dst_id, 1 AS depth, ARRAY[src_id, dst_id] AS path
  FROM rcb_pointer_edge
  WHERE person_id = $1 AND src_id = ANY($2::text[])
  UNION ALL
  SELECT e.src_id, e.dst_id, w.depth + 1, w.path || e.dst_id
  FROM rcb_pointer_edge e
  JOIN walk w ON e.person_id = $1 AND e.src_id = w.dst_id
  WHERE w.depth < $3 AND NOT (e.dst_id = ANY(w.path))
)
SELECT DISTINCT dst_id FROM walk
`.trim();

const EVENT_BY_ID = "SELECT id FROM rcb_vault_event WHERE id = $1";
const INSERT_EVENT = `
INSERT INTO rcb_vault_event
  (id, person_id, note_text, source_type, captured_at, lineage_id, document_id, content_hash)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
`.trim();
const NEXT_SEQUENCE = `
SELECT COALESCE(MAX(sequence), 0) AS max_sequence
FROM rcb_link_advertisement
WHERE person_id = $1
`.trim();
const INSERT_AD = `
INSERT INTO rcb_link_advertisement (
  id, sequence, person_id, origin, digest, model_version, prompt_version, policy_version,
  evidence_ids, from_id, to_id, judgment, reason_code, relation, proposed_confidence,
  confidence, created_at, supersedes_id, withdrawn
) VALUES (
  $1, $2, $3, $4, $5, $6, $7, $8,
  $9::jsonb, $10, $11, $12, $13, $14, $15,
  $16, $17, $18, $19
)
`.trim();
const DELETE_EDGE = `
DELETE FROM rcb_pointer_edge
WHERE person_id = $1 AND (
  (src_id = $2 AND dst_id = $3) OR (src_id = $3 AND dst_id = $2)
)
`.trim();
const UPSERT_EDGE = `
INSERT INTO rcb_pointer_edge
  (person_id, src_id, dst_id, ad_id, confidence, reason_code, relation)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (person_id, src_id, dst_id) DO UPDATE SET
  ad_id = EXCLUDED.ad_id,
  confidence = EXCLUDED.confidence,
  reason_code = EXCLUDED.reason_code,
  relation = EXCLUDED.relation
`.trim();
const NEIGHBORS = `
SELECT dst_id FROM rcb_pointer_edge
WHERE person_id = $1 AND src_id = ANY($2::text[])
ORDER BY dst_id
`.trim();

function dropsAcceptedEdge(ad: Pick<LinkAdvertisement, "withdrawn" | "origin" | "judgment">): boolean {
  return ad.withdrawn || (ad.origin === "user_correction" && ad.judgment !== "link");
}

function advertisementDigest(draft: AdvertisementDraft, sequence: number): string {
  return sha256(
    JSON.stringify({
      origin: draft.origin,
      evidenceIds: [...draft.evidenceIds].sort(),
      fromId: draft.fromId,
      toId: draft.toId,
      judgment: draft.judgment,
      reasonCode: draft.reasonCode,
      relation: draft.relation,
      confidence: draft.confidence,
      withdrawn: draft.withdrawn,
      supersedesId: draft.supersedesId,
      sequence,
    }),
  );
}

export class PostgresPointerStore {
  constructor(private readonly db: Queryable) {}

  async appendEvent(event: VaultEvent): Promise<void> {
    const existing = await this.db.query(EVENT_BY_ID, [event.id]);
    if (existing.rows.length > 0) throw new Error("vault is append-only");
    await this.db.query(INSERT_EVENT, [
      event.id,
      event.personId,
      event.text,
      event.sourceType,
      event.capturedAt,
      event.lineageId,
      event.documentId,
      event.contentHash,
    ]);
  }

  async appendAdvertisement(personId: string, draft: AdvertisementDraft): Promise<LinkAdvertisement> {
    const seqRows = await this.db.query<{ max_sequence: number }>(NEXT_SEQUENCE, [personId]);
    const sequence = Number(seqRows.rows[0]?.max_sequence ?? 0) + 1;
    const ad: LinkAdvertisement = {
      ...draft,
      evidenceIds: [...draft.evidenceIds],
      id: `ad-${personId}-${sequence}`,
      sequence,
      digest: advertisementDigest(draft, sequence),
    };
    await this.db.query(INSERT_AD, [
      ad.id,
      ad.sequence,
      personId,
      ad.origin,
      ad.digest,
      ad.modelVersion,
      ad.promptVersion,
      ad.policyVersion,
      JSON.stringify(ad.evidenceIds),
      ad.fromId,
      ad.toId,
      ad.judgment,
      ad.reasonCode,
      ad.relation,
      ad.proposedConfidence,
      ad.confidence,
      ad.createdAt,
      ad.supersedesId,
      ad.withdrawn,
    ]);
    if (dropsAcceptedEdge(ad)) {
      await this.db.query(DELETE_EDGE, [personId, ad.fromId, ad.toId]);
    } else if (ad.judgment === "link") {
      const fields = [personId, ad.id, ad.confidence, ad.reasonCode, ad.relation] as const;
      await this.db.query(UPSERT_EDGE, [fields[0], ad.fromId, ad.toId, ...fields.slice(1)]);
      await this.db.query(UPSERT_EDGE, [fields[0], ad.toId, ad.fromId, ...fields.slice(1)]);
    }
    return ad;
  }

  async neighbors(personId: string, srcIds: string[]): Promise<string[]> {
    if (srcIds.length === 0) return [];
    const result = await this.db.query<{ dst_id: string }>(NEIGHBORS, [personId, srcIds]);
    return result.rows.map((row) => row.dst_id);
  }

  async walk(personId: string, srcIds: string[], depth: number): Promise<string[]> {
    if (srcIds.length === 0 || depth < 1) return [];
    const result = await this.db.query<{ dst_id: string }>(WALK_SQL, [personId, srcIds, depth]);
    return result.rows.map((row) => row.dst_id);
  }
}

/** Rebuilds the in-memory projection from advertisements. Digest follows store.ts. */
export function replay(ads: readonly LinkAdvertisement[]): Projection {
  const projection = new Projection();
  projection.rebuild(ads);
  return projection;
}

export async function connectPostgres(connectionString: string): Promise<Queryable> {
  const pg = (await import("pg")) as {
    Pool: new (config: { connectionString: string }) => Queryable;
  };
  return new pg.Pool({ connectionString });
}
