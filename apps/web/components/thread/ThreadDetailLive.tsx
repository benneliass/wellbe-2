"use client";

import Link from "next/link";
import { Chip, Icon } from "@wellbe/ui";
import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { StateNote } from "@/components/placeholder/StateNote";
import { formatShortDate, mapThreadStatus } from "@/lib/adapters";
import { memoryTypeLabel, nodeTypeLabel, relationPhrase, sourceRefSummary } from "@/lib/graph-labels";
import { STATUS_META } from "@/lib/meta";
import { usePendingItems, useThread, useThreadGraph, useThreadMemories } from "@/lib/hooks";
import { Panel } from "./Panel";
import detail from "./ThreadDetail.module.css";
import rec from "@/components/records/RecordList.module.css";
import styles from "./ThreadDetailLive.module.css";
import { describePendingItem, openPendingItems } from "@/lib/pending";
import { cleanTheoryLabel } from "@/lib/theory-label";
import { ThreadTheories } from "./ThreadTheories";

/**
 * Live thread detail for real (non-demo) thread ids: the /v1/threads/{id}
 * header, the memories kept around it (/v2/threads/{id}/memories), what it
 * connects to in the person's graph (/v2/graph/threads/{id}), and its open loops.
 * Every item is source-linked; nothing here is a diagnosis.
 */
export function ThreadDetailLive({ id }: { id: string }) {
  const { data, isLoading, isError } = useThread(id);
  const memories = useThreadMemories(id);
  const graph = useThreadGraph(id);
  const pending = usePendingItems();

  if (isLoading) {
    return (
      <>
        <TopBar title="Loading thread…" breadcrumb="Threads" backHref="/workspace" />
        <PageBody>
          <StateNote icon="clock" title="Loading this thread…" />
        </PageBody>
      </>
    );
  }

  if (isError || !data) {
    return (
      <>
        <TopBar title="Thread" breadcrumb="Threads" backHref="/workspace" />
        <PageBody>
          <StateNote
            icon="alert-circle"
            title="Couldn't load this thread"
            description="Something went wrong reaching the server. Please try again in a moment."
          />
        </PageBody>
      </>
    );
  }

  const status = STATUS_META[mapThreadStatus(data.status)];
  const started = formatShortDate(data.created_at);
  const updated = formatShortDate(data.updated_at);
  const nodes = graph.data?.nodes ?? [];
  const edges = graph.data?.edges ?? [];
  const nodeLabel = (n: { type: string; label: string }) =>
    n.type === "Theory" ? cleanTheoryLabel(n.label) : n.label;
  const labelById = new Map(nodes.map((n) => [n.id, nodeLabel(n)]));
  const loops = openPendingItems((pending.data ?? []).filter((p) => p.primary_thread_id === id));
  const askHref = `/ask?q=${encodeURIComponent(`What is going on with my ${data.title.toLowerCase()}?`)}`;

  return (
    <>
      <TopBar
        title={data.title}
        breadcrumb="Threads"
        subtitle={[started && `Started ${started}`, updated && `Updated ${updated}`]
          .filter(Boolean)
          .join(" · ")}
        backHref="/workspace"
      />
      <PageBody>
        <div className={detail.detail}>
          <div className={detail.main}>
            <Panel
              title="Memories"
              icon="book"
              count={memories.data ? `${memories.data.length} kept` : undefined}
            >
              {memories.isLoading ? (
                <p className={rec.muted}>Loading memories…</p>
              ) : memories.isError ? (
                <p className={rec.muted}>Memories aren&rsquo;t available right now.</p>
              ) : (memories.data ?? []).length === 0 ? (
                <p className={rec.muted}>
                  Nothing kept for this thread yet. What you add will gather here, source-linked.
                </p>
              ) : (
                <ul className={rec.list}>
                  {(memories.data ?? []).map((m) => {
                    const kept = m.created_at ? formatShortDate(m.created_at) : "";
                    return (
                      <li key={m.memory_entry_id} className={rec.row}>
                        <span className={rec.rowIcon}>
                          <Icon name="book" size={15} />
                        </span>
                        <span className={rec.rowMain}>
                          <span className={rec.rowTitle}>{m.title}</span>
                          <span className={rec.rowSub}>
                            <Icon name="badge-check" size={11} />
                            {sourceRefSummary(m.source_refs ?? []) || "Source-linked"}
                            {kept ? ` · ${kept}` : ""}
                          </span>
                        </span>
                        <Chip size="sm" tone="tealmid">
                          {memoryTypeLabel(m.memory_type)}
                        </Chip>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Panel>

            <Panel
              title="Connected in your records"
              icon="git-fork"
              count={graph.data ? `${nodes.length} ${nodes.length === 1 ? "item" : "items"}` : undefined}
            >
              {graph.isLoading ? (
                <p className={rec.muted}>Loading connections…</p>
              ) : graph.isError ? (
                <p className={rec.muted}>Connections aren&rsquo;t available right now.</p>
              ) : nodes.length === 0 ? (
                <p className={rec.muted}>No connected items yet.</p>
              ) : (
                <>
                  <ul className={rec.list}>
                    {nodes.map((n) => {
                      const seen = n.attributes?.first_seen_at;
                      const first = typeof seen === "string" ? formatShortDate(seen) : "";
                      const elsewhere = n.attributes?.in_thread === false;
                      return (
                        <li key={n.id} className={rec.row}>
                          <span className={rec.rowIcon}>
                            <Icon name="activity" size={15} />
                          </span>
                          <span className={rec.rowMain}>
                            <span className={rec.rowTitle}>{nodeLabel(n)}</span>
                            <span className={rec.rowSub}>
                              {nodeTypeLabel(n.type)}
                              {first ? ` · first noted ${first}` : ""}
                              {elsewhere ? " · elsewhere in your records" : ""}
                            </span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  {edges.length > 0 && (
                    <ul className={styles.edges}>
                      {edges.map((e) => (
                        <li key={e.id}>
                          <b>{labelById.get(e.source) ?? "An item"}</b> {relationPhrase(e.relation)}{" "}
                          <b>{labelById.get(e.target) ?? "another item"}</b>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className={styles.caveat}>
                    Connections in your own records — not causes, and not a diagnosis.
                  </p>
                </>
              )}
            </Panel>

            <ThreadTheories threadId={id} />
          </div>

          <aside className={detail.side}>
            <Panel title="Status" icon={status.icon}>
              <div className={styles.status}>
                <Chip tone={status.tone}>{status.label}</Chip>
                <span className={rec.rowSub}>{humanStatus(data.status)}</span>
              </div>
            </Panel>

            <Panel title="Open loops" icon="clock" count={`${loops.length}`}>
              {loops.length === 0 ? (
                <p className={rec.muted}>Nothing waiting on this thread.</p>
              ) : (
                <ul className={rec.list}>
                  {loops.map((p) => (
                    <li key={p.pending_item_id} className={rec.row}>
                      <span className={rec.rowIcon}>
                        <Icon name="clock" size={15} />
                      </span>
                      <span className={rec.rowMain}>
                        <span className={rec.rowTitle}>{p.title}</span>
                      </span>
                      <Chip size="sm" tone={describePendingItem(p).tone}>
                        {describePendingItem(p).label}
                      </Chip>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="What next?" icon="circle-help">
              <div className={styles.next}>
                <Link href={askHref} className={styles.nextLink}>
                  <Icon name="message-circle" size={15} /> Ask about this thread
                </Link>
                <Link href="/prepare" className={styles.nextLink}>
                  <Icon name="user" size={15} /> Prepare for an appointment
                </Link>
              </div>
            </Panel>
          </aside>
        </div>
      </PageBody>
    </>
  );
}

function humanStatus(raw: string): string {
  const s = raw.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
