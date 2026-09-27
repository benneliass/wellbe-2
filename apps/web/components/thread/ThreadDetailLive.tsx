"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  Chip,
  DisclosureRegion,
  EvidenceDrawer,
  Icon,
  JourneyRail,
  SourceMarker,
  StoryLanes,
  laneForAuthorship,
  type EvidenceSource,
  type JourneyStage,
  type StoryEntry,
} from "@wellbe/ui";
import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { StateNote } from "@/components/placeholder/StateNote";
import { formatShortDate } from "@/lib/adapters";
import { usePendingItems, useThread, useThreadGraph, useThreadMemories } from "@/lib/hooks";
import { describePendingItem, openPendingItems } from "@/lib/pending";
import { useThreadInvestigations } from "@/lib/theories";
import { cleanTheoryLabel } from "@/lib/theory-label";
import { useThreadTimeline } from "@/lib/thread-hooks";
import { LiveTimeline, timelineAnchor } from "./LiveTimeline";
import { Panel } from "./Panel";
import { ThreadCaptureSheet } from "./ThreadCaptureSheet";
import { ThreadConnections, type ConnectionNode } from "./ThreadConnections";
import { ThreadTheories } from "./ThreadTheories";
import {
  buildSourceIndex,
  clarifyQuestion,
  eventStage,
  eventTitle,
  isThreadStatus,
  latestChange,
  resolveSources,
  statusHistory,
  storyEntries,
  waitingOn,
} from "./thread-view";
import detail from "./ThreadDetail.module.css";
import rec from "@/components/records/RecordList.module.css";
import styles from "./ThreadDetailLive.module.css";

/** Entries per lane shown before "Show all" — keeps L0–L2 above the fold on mobile. */
const STORY_PREVIEW = 2;

interface DrawerState {
  title: string;
  claim: string;
  sources: EvidenceSource[];
}

function previewEntries(entries: readonly StoryEntry[]): StoryEntry[] {
  const perLane = new Map<string, number>();
  return entries.filter((e) => {
    const lane = laneForAuthorship(e.authorship);
    const n = perLane.get(lane) ?? 0;
    perLane.set(lane, n + 1);
    return n < STORY_PREVIEW;
  });
}

/**
 * Live thread detail for real (non-demo) thread ids, laid out by the progressive
 * disclosure contract: journey rail + next action (L0–L2), the clarify strip and
 * Story Memory lanes (L1), then timeline (L3) and connections (L4) behind explicit
 * expanders. Every derived item carries review markers and opens its sources.
 * Nothing here is a diagnosis.
 */
export function ThreadDetailLive({ id }: { id: string }) {
  const { data, isLoading, isError } = useThread(id);
  const memories = useThreadMemories(id);
  const graph = useThreadGraph(id);
  const pending = usePendingItems();
  const timeline = useThreadTimeline(id);
  const investigations = useThreadInvestigations(id);

  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const [capture, setCapture] = useState<{ prompt?: string } | null>(null);
  const [clarifyDismissed, setClarifyDismissed] = useState(false);
  const [showAllStory, setShowAllStory] = useState(false);
  // Remounts the timeline region open when the user taps a rail stage.
  const [timelineOpenedBy, setTimelineOpenedBy] = useState(0);
  const [jumpTo, setJumpTo] = useState<string | null>(null);

  useEffect(() => {
    if (!jumpTo) return;
    const el = document.getElementById(timelineAnchor(jumpTo));
    el?.scrollIntoView?.({ block: "center" });
    el?.focus({ preventScroll: true });
    setJumpTo(null);
  }, [jumpTo, timelineOpenedBy]);

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

  const openEvidence = (title: string, claim: string, sources: EvidenceSource[]) =>
    setDrawer({ title, claim, sources });

  const started = formatShortDate(data.created_at);
  const updated = formatShortDate(data.updated_at);
  const index = buildSourceIndex(timeline.data);
  const history = statusHistory(timeline.data);
  const events = timeline.data?.events ?? [];
  const entries = storyEntries(memories.data ?? [], index);
  const shownEntries = showAllStory ? entries : previewEntries(entries);
  const loops = openPendingItems((pending.data ?? []).filter((p) => p.primary_thread_id === id));
  const actionDue = loops.some((p) => p.status === "due" || p.status === "overdue");
  const clarify =
    memories.isSuccess && investigations.isSuccess && !clarifyDismissed
      ? clarifyQuestion({ title: data.title, entries, investigations: investigations.data })
      : null;

  const change = latestChange(timeline.data);
  const changeSources = change ? resolveSources(change.source_ref_ids ?? [], index) : [];
  const changeLead = changeSources[0];
  const changeDate = change ? formatShortDate(change.occurred_at) : "";
  const whatChanged = change ? (
    <span className={styles.changed}>
      <span>
        {eventTitle(change)}
        {changeDate ? ` · ${changeDate}` : ""}
      </span>
      {changeLead && (
        <SourceMarker
          displayLabel={changeLead.displayLabel}
          component={changeLead.component}
          kind={changeLead.kind}
          count={changeSources.length}
          onOpen={() => openEvidence("Where this came from", eventTitle(change), changeSources)}
        />
      )}
    </span>
  ) : undefined;

  const nextAction =
    loops.length > 0 ? (
      <a href="#open-loops" className={styles.nextPrimary}>
        <Icon name="clock" size={15} />
        {loops.length === 1 ? "See what's pending" : `See what's pending (${loops.length})`}
      </a>
    ) : (
      <Button size="sm" icon="plus" onClick={() => setCapture({})}>
        Add an update
      </Button>
    );

  const jumpToStage = (stage: JourneyStage) => {
    const target = events.find((ev) => eventStage(ev, history) === stage);
    setTimelineOpenedBy((n) => n + 1);
    if (target) setJumpTo(target.event_id);
  };

  const nodes: ConnectionNode[] = graph.data?.nodes ?? [];
  const edges = graph.data?.edges ?? [];
  const nodeLabel = (n: ConnectionNode) => (n.type === "Theory" ? cleanTheoryLabel(n.label) : n.label);
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
            <section className={styles.journey} aria-label="Where this thread is" data-disclosure-level="L0">
              {isThreadStatus(data.status) ? (
                <JourneyRail
                  status={data.status}
                  history={history}
                  variant="full"
                  whatChanged={whatChanged}
                  waitingOn={waitingOn(loops, data.status)}
                  actionDue={actionDue}
                  nextAction={nextAction}
                  onSelectStage={jumpToStage}
                />
              ) : (
                <div className={styles.changed}>{nextAction}</div>
              )}
            </section>

            {clarify && (
              <section className={styles.clarify} aria-label="One question for you" data-disclosure-level="L1">
                <span className={styles.clarifyIcon} aria-hidden="true">
                  <Icon name="circle-help" size={16} />
                </span>
                <div className={styles.clarifyBody}>
                  <p className={styles.clarifyQuestion}>{clarify.question}</p>
                  <p className={styles.clarifyWhy}>{clarify.why}</p>
                  <div className={styles.clarifyActions}>
                    <Button size="sm" variant="secondary" onClick={() => setCapture({ prompt: clarify.question })}>
                      Answer in your words
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setClarifyDismissed(true)}>
                      Not now
                    </Button>
                  </div>
                </div>
              </section>
            )}

            <section className={styles.story} aria-labelledby="thread-story-title" data-disclosure-level="L1">
              <div className={styles.sectionHead}>
                <h2 id="thread-story-title" className={styles.sectionTitle}>
                  <Icon name="book" size={16} /> Your story
                </h2>
                {memories.data && <span className={styles.count}>{entries.length} kept</span>}
              </div>
              {memories.isLoading ? (
                <p className={styles.muted}>Loading your story…</p>
              ) : memories.isError ? (
                <p className={styles.muted}>Your story isn&rsquo;t available right now.</p>
              ) : (
                <>
                  <StoryLanes
                    entries={shownEntries}
                    onOpenSources={(e) => openEvidence("Where this came from", e.text, e.sources ?? [])}
                    onAddToStory={() => setCapture({})}
                  />
                  {shownEntries.length < entries.length && (
                    <Button size="sm" variant="ghost" icon="chevron-down" onClick={() => setShowAllStory(true)}>
                      Show all {entries.length}
                    </Button>
                  )}
                </>
              )}
            </section>

            <DisclosureRegion
              key={`timeline-${timelineOpenedBy}`}
              level="L3"
              defaultOpen={timelineOpenedBy > 0}
              expandLabel="Show timeline"
              summary={
                <div className={styles.regionSummary}>
                  <h2 className={styles.sectionTitle}>
                    <Icon name="calendar" size={16} /> Timeline
                  </h2>
                  <span className={styles.count}>
                    {timeline.isLoading
                      ? "Loading…"
                      : timeline.isError
                        ? "Not available right now"
                        : `${events.length} ${events.length === 1 ? "event" : "events"}`}
                  </span>
                </div>
              }
            >
              {timeline.data && (
                <LiveTimeline events={events} index={index} onOpenEvidence={openEvidence} />
              )}
            </DisclosureRegion>

            <DisclosureRegion
              level="L4"
              expandLabel="Explore connections"
              summary={
                <div className={styles.regionSummary}>
                  <h2 className={styles.sectionTitle}>
                    <Icon name="git-fork" size={16} /> Connected in your records
                  </h2>
                  <span className={styles.count}>
                    {graph.isLoading
                      ? "Loading…"
                      : graph.isError
                        ? "Not available right now"
                        : `${nodes.length} ${nodes.length === 1 ? "item" : "items"}`}
                  </span>
                </div>
              }
            >
              {graph.data && (
                <ThreadConnections
                  nodes={nodes}
                  edges={edges}
                  index={index}
                  labelOf={nodeLabel}
                  onOpenEvidence={openEvidence}
                />
              )}
            </DisclosureRegion>

            <ThreadTheories
              threadId={id}
              sourceIndex={index}
              controllerId={data.patient_id}
              onOpenEvidence={openEvidence}
            />
          </div>

          <aside className={detail.side}>
            <div id="open-loops">
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
            </div>

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

      <EvidenceDrawer
        open={drawer !== null}
        onClose={() => setDrawer(null)}
        title={drawer?.title}
        claim={drawer?.claim}
        sources={drawer?.sources ?? []}
      />
      {capture && (
        <ThreadCaptureSheet
          threadId={id}
          threadTitle={data.title}
          prompt={capture.prompt}
          onClose={() => setCapture(null)}
        />
      )}
    </>
  );
}
