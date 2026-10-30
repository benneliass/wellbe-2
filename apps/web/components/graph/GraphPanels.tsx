"use client";
import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";
import { Button, Chip, ConfidenceDots, Icon, SourceMarker, type EvidenceSource } from "@wellbe/ui";
import { FAMILY, NEUTRAL_HUE, THEORY_HUE, TYPE_ICON, type Cluster, type ClusterId, type GraphEdge, type GraphNode, type NodeAction } from "./graphData";
import { graphObjectColor } from "./graphAppearance";
import { graphEvidence as evidenceOf } from "./graphMiniatures";
import { canvasLabel } from "./liveGraphLayout";
import { typeLabelOf, plural } from "./graphPresentation";
import styles from "./GraphLive.module.css";

/* ---------- radial menu ---------- */
export function RadialMenu({ radial, actions, onAction, onClose }: { radial: { id: string; xPct: number; yPct: number }; actions: NodeAction[]; onAction: (a: string, id: string) => void; onClose: () => void }) {
  const radius = 82;
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => first.current?.focus(), []);
  return (
    <div className={styles.radialWrap} onClick={onClose} onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}>
      <div className={styles.radial} role="menu" aria-label="Quick actions" style={{ left: `${radial.xPct}%`, top: `${radial.yPct}%` }}>
        <span className={styles.radialCenter}><Icon name="git-fork" size={15} /></span>
        {actions.map((a, idx) => {
          const ang = -Math.PI / 2 + (idx / actions.length) * Math.PI * 2;
          return (
            <button key={a.id} ref={idx === 0 ? first : undefined} type="button" role="menuitem" className={styles.radialBtn} style={{ transform: `translate(${Math.cos(ang) * radius}px, ${Math.sin(ang) * radius}px)` }} title={a.label} aria-label={a.label} onClick={(e) => { e.stopPropagation(); onAction(a.id, radial.id); }}>
              <Icon name={a.icon} size={16} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- banners ---------- */
export function Banner({ icon, tone, text, actionLabel, onAction, onCancel }: { icon: string; tone: "violet" | "teal"; text: string; actionLabel?: string; onAction?: () => void; onCancel?: () => void }) {
  return (
    <div className={styles.banner} data-tone={tone}>
      <Icon name={icon} size={15} />
      <span className={styles.bannerText}>{text}</span>
      {actionLabel && <Button variant="primary" size="sm" onClick={onAction}>{actionLabel}</Button>}
      {onCancel && <button type="button" className={styles.bannerCancel} onClick={onCancel} aria-label="Dismiss"><Icon name="x" size={15} /></button>}
    </div>
  );
}
export function ConsentBanner({ onAccept, onCancel }: { onAccept: () => void; onCancel: () => void }) {
  return (
    <div className={styles.banner} data-tone="violet">
      <Icon name="shield-check" size={15} />
      <span className={styles.bannerText}>Comparison is <strong>opt-in and aggregate-only</strong> — “people with a similar pattern often also tracked…”. Never identifies anyone, never shared with your clinic or employer.</span>
      <Button variant="primary" size="sm" onClick={onAccept}>Turn on</Button>
      <button type="button" className={styles.bannerCancel} onClick={onCancel} aria-label="Cancel"><Icon name="x" size={15} /></button>
    </div>
  );
}

/* ---------- inspector panels ---------- */
export function OverviewPanel({ conceptCount, openLoopCount, clusterCount, bridge, bridgeConcerns, bridgeCount }: { conceptCount: number; openLoopCount: number; clusterCount: number; bridge?: GraphNode; bridgeConcerns: string[]; bridgeCount: number }) {
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="git-fork" size={16} /></span><div><p className={styles.inspTitleSerif}>Your whole-person map</p><p className={styles.inspSub}>Scoped to you · traceable to its sources</p></div></div>
      <div className={styles.statRow}>
        <div className={styles.stat}><span className={styles.statValue}>{clusterCount}</span><span className={styles.statLabel}>{clusterCount === 1 ? "concern" : "concerns"}</span></div>
        <div className={styles.stat}><span className={styles.statValue}>{conceptCount}</span><span className={styles.statLabel}>{conceptCount === 1 ? "concept" : "concepts"}</span></div>
        <div className={styles.stat}><span className={styles.statValue}>{openLoopCount}</span><span className={styles.statLabel}>{openLoopCount === 1 ? "open loop" : "open loops"}</span></div>
      </div>
      <p className={styles.inspBody}>
        Tap a <strong>node</strong> for details and sources. Source records stay in orbit; related items can open on the map. Tap a <strong>line</strong> for why two items connect. Right-click or long-press for quick actions.
        {bridge && bridgeConcerns.length >= 2 && <> <span className={styles.bridgeName}>{bridge.label}</span> bridges {bridgeConcerns.join(" and ")}{bridgeCount > 1 ? `, one of ${bridgeCount} shared items` : ""}.</>}
      </p>
      <p className={styles.tipLine}><Icon name="search" size={13} /> Scroll to zoom · drag the background to pan · drag a node or concern title to move it (arrow keys nudge a focused node) · Tab or Alt+arrow keys move between nodes · use Layers, Lens and Replay to explore.</p>
      <div className={styles.safety}><Icon name="shield-check" size={14} /><span>This map shows how items appear in your records — not medical severity. Links are not causes, and never a diagnosis.</span></div>
    </>
  );
}

export function ExplainPanel({ narration, onClose }: { narration: string; onClose: () => void }) {
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="sparkles" size={16} /></span><div><p className={styles.inspTitle}>Explain my graph</p><p className={styles.inspSub}>Plain-language, from your records</p></div></div>
      <p className={styles.inspBody}>{narration}</p>
      <div className={styles.safety}><Icon name="info" size={14} /><span>This narration describes what&apos;s in your records in plain language. It doesn&apos;t diagnose or claim cause.</span></div>
      <Button variant="ghost" icon="x" onClick={onClose}>Close narration</Button>
    </>
  );
}

function SourceList({ sources, limit, onOpen }: { sources: EvidenceSource[]; limit?: number; onOpen: () => void }) {
  const shown = limit ? sources.slice(0, limit) : sources;
  return (
    <ul className={styles.capList}>
      {shown.map((s) => (
        <li key={s.id} className={styles.capRow}>
          <SourceMarker displayLabel={s.displayLabel} component={s.component} kind={s.kind} date={s.date} onOpen={onOpen} />
          {s.excerpt && <span className={styles.capText}>{s.excerpt}</span>}
        </li>
      ))}
    </ul>
  );
}

export function NodePanel({ node, edges, nodeById, floor, showWeak, evidenceAll, expandedNode, expandable, actions, hueOf, clusterLabel, concernHref, onAction, onSelectNeighbour, onSelectEdge, onShowWeak, onToggleEvidence, onToggleExpand, onOpenEvidence, onTogglePin }: {
  onTogglePin?: () => void;
  node: GraphNode; edges: GraphEdge[]; nodeById: Record<string, GraphNode>; floor: number; showWeak: boolean; evidenceAll: boolean; expandedNode: boolean; expandable: boolean; actions: NodeAction[];
  hueOf: (id: ClusterId | undefined) => string; clusterLabel: (id: ClusterId) => string; concernHref?: string;
  onAction: (a: string, id: string) => void; onSelectNeighbour: (id: string) => void; onSelectEdge: (e: GraphEdge) => void; onShowWeak: () => void; onToggleEvidence: () => void; onToggleExpand: () => void;
  onOpenEvidence: (title: string, claim: ReactNode, sources: EvidenceSource[]) => void;
}) {
  const theory = node.lensRole === "theory";
  const hue = graphObjectColor(node, nodeById, hueOf);
  const membership = node.bridge ? node.bridge.map(clusterLabel) : node.cluster ? [clusterLabel(node.cluster)] : ["Also in your records"];
  const related = edges
    .map((e) => (e.a === node.id ? { id: e.b, e } : e.b === node.id ? { id: e.a, e } : null))
    .filter((x): x is { id: string; e: GraphEdge } => x !== null && Boolean(nodeById[x.id]))
    .sort((p, q) => q.e.s - p.e.s);
  const shown = related.filter((r) => r.e.s >= floor || r.e.f === "user" || r.e.f === "hypothesis" || r.e.f === "relevance").slice(0, 12);
  const hiddenCount = Math.max(Math.max(node.relatedTotal, related.length) - shown.length, 0);
  const evidence = evidenceOf(node);
  const openAll = () => onOpenEvidence(`Sources for ${node.label}`, `Where “${node.label}” appears in your records.`, evidence);

  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge} style={{ background: `${hue}1f`, color: hue }}><Icon name={TYPE_ICON[node.type]} size={16} /></span><div><p className={styles.inspTitle}>{node.label}</p><p className={styles.inspSub}>{typeLabelOf(node)}</p></div></div>
      <div className={styles.chipRow}>
        {membership.map((m) => <Chip key={m} tone="neutral" size="sm" dot>{m}</Chip>)}
        {node.bridge && !theory && <Chip tone="violet" size="sm" icon="git-fork">Bridge</Chip>}
        {onTogglePin ? <button type="button" className={styles.pinToggle} onClick={onTogglePin} aria-pressed={Boolean(node.pinned)} aria-label={`${node.pinned ? 'Unpin' : 'Pin'} ${node.label}`}><Chip tone="neutral" size="sm" icon="star">{node.pinned ? 'Pinned on map' : 'Pin on map'}</Chip></button> : node.pinned && <Chip tone="neutral" size="sm" icon="star">Pinned</Chip>}
        {node.aggregate && <Chip tone="neutral" size="sm" icon="users">Aggregate</Chip>}
      </div>

      {node.aggregate ? (
        <div className={styles.conflictNote}><Icon name="users" size={14} /><span>An opt-in, aggregate pattern from people with similar records — not from your data, and not a recommendation.</span></div>
      ) : node.ghost ? (
        <div className={styles.openLoopNote}><Icon name="clock" size={14} /><span>{node.statusNote ? `${node.statusNote} — ` : "Awaiting result — "}worth a follow-up. Not an alarm.</span></div>
      ) : (
        <>
          {theory && <div className={styles.openLoopNote}><Icon name="flask-conical" size={14} /><span>A working idea inside an investigation — never a conclusion or a diagnosis.</span></div>}
          <div className={styles.section}>
            <div className={styles.sectionHead}><span>Related</span><span className={styles.sectionCount}>Showing {shown.length} of {Math.max(node.relatedTotal, related.length)}</span></div>
            {shown.length === 0 && <p className={styles.inspBody}>No links above the current strength setting.</p>}
            <ul className={styles.neighList}>
              {shown.map((r) => { const nb = nodeById[r.id]!; const fam = FAMILY[r.e.f]; return (
                <li key={`${r.id}-${r.e.id ?? r.e.f}`} className={styles.neighItem}>
                  <button type="button" className={styles.neighRow} onClick={() => onSelectNeighbour(r.id)}><span className={styles.neighDot} style={{ background: graphObjectColor(nb, nodeById, hueOf) }} /><span className={styles.neighName}>{nb.label}</span><span className={styles.neighFam} data-fam={r.e.f}>{fam.label}</span></button>
                  <button type="button" className={styles.neighWhy} onClick={() => onSelectEdge(r.e)} aria-label={`Why is ${node.label} connected to ${nb.label}?`}>Why?</button>
                </li>
              ); })}
            </ul>
            {hiddenCount > 0 && !showWeak && <Button variant="tertiary" size="sm" icon="plus" onClick={onShowWeak}>Show {hiddenCount} weaker link{hiddenCount > 1 ? "s" : ""}</Button>}
          </div>

          <div className={styles.section}>
            <div className={styles.sectionHead}><span>Evidence</span><ConfidenceDots level={node.conf} label={plural(evidence.length, "source")} /></div>
            {evidence.length ? (
              <SourceList sources={evidence} limit={evidenceAll ? undefined : 3} onOpen={openAll} />
            ) : (
              <p className={styles.inspBody}>No sources are attached to this yet{node.relatedTotal ? " — it's mapped from how it links to your other records" : ""}.</p>
            )}
            <div className={styles.evRow}>
              {evidence.length > 0 && <Button variant="tertiary" size="sm" icon="file-search" onClick={openAll}>View sources</Button>}
              {evidence.length > 3 && <Button variant="tertiary" size="sm" icon={evidenceAll ? "chevron-down" : "file-text"} onClick={onToggleEvidence}>{evidenceAll ? "Show fewer" : `Complete evidence mode (${evidence.length})`}</Button>}
              {expandable && <Button variant="tertiary" size="sm" icon="git-fork" onClick={onToggleExpand}>{expandedNode ? "Collapse on map" : "Expand on map"}</Button>}
            </div>
          </div>
        </>
      )}

      <div className={styles.metaBlock}>
        <div className={styles.metaRow}><span className={styles.metaKey}>First noted</span><span className={styles.metaVal}>{node.first}</span></div>
        <div className={styles.metaRow}><span className={styles.metaKey}>{node.ghost ? "Status" : "Last activity"}</span><span className={styles.metaVal}>{node.last}</span></div>
        {concernHref && <div className={styles.metaRow}><span className={styles.metaKey}>Concern</span><Link className={styles.metaLink} href={concernHref}>Open {membership[0]}</Link></div>}
      </div>

      <div className={styles.actionList}>{actions.map((a) => <button key={a.id} type="button" className={styles.action} data-danger={a.id === "hide" || undefined} onClick={() => onAction(a.id, node.id)}><Icon name={a.icon} size={15} /> {a.label}</button>)}</div>
      <p className={styles.caveatLine}><Icon name="lock" size={12} /> Links are not causes, and never a diagnosis.</p>
    </>
  );
}

export function EdgePanel({ edge, nodeById, canDispute, disputed, onDispute, onOpenEvidence, onSelectNode }: {
  edge: GraphEdge; nodeById: Record<string, GraphNode>; canDispute: boolean; disputed: boolean; onDispute: () => void;
  onOpenEvidence: (title: string, claim: ReactNode, sources: EvidenceSource[]) => void; onSelectNode: (id: string) => void;
}) {
  const a = nodeById[edge.a];
  const b = nodeById[edge.b];
  const fam = FAMILY[edge.f];
  const strengthLabel = edge.s >= 5 ? "Well-supported in your records" : edge.s >= 4 ? "Some support in your records" : "Candidate — weak or system-inferred";
  const dots = Math.max(1, Math.round((edge.s / 7) * 5));
  const sources = edge.evidence ?? [...(a ? evidenceOf(a) : []), ...(b ? evidenceOf(b) : [])];
  const claim = a && b ? `${a.label} ${edge.phrase ?? "is linked with"} ${b.label} in your records.` : "How these items are linked in your records.";
  const openAll = () => onOpenEvidence("Why connected?", claim, sources);
  return (
    <>
      <div className={styles.inspHead}><span className={styles.inspBadge}><Icon name="share" size={16} /></span><div><p className={styles.inspTitle}>Why connected?</p><p className={styles.inspSub}>{a?.label} · {b?.label}</p></div></div>
      <div className={styles.chipRow}><Chip tone={fam.tone} size="sm">{fam.label}</Chip>{edge.lens && <Chip tone={edge.lens === "for" ? "tealmid" : "neutral"} size="sm">Evidence {edge.lens}</Chip>}{disputed && <Chip tone="amber" size="sm" icon="alert-triangle">Disputed</Chip>}</div>
      {a && b && edge.phrase && (
        <p className={styles.inspBody}>
          <button type="button" className={styles.inlineNode} onClick={() => onSelectNode(a.id)}>{a.label}</button> {edge.phrase}{" "}
          <button type="button" className={styles.inlineNode} onClick={() => onSelectNode(b.id)}>{b.label}</button>.
        </p>
      )}
      <p className={styles.inspBody}>{fam.note}</p>
      {edge.f === "conflict" && <div className={styles.conflictNote}><Icon name="alert-triangle" size={14} /><span>Both sources are kept. WellBe shows the disagreement rather than resolving it for you.</span></div>}
      {edge.confounder && <p className={styles.inspBody}>{edge.confounder}</p>}
      {edge.alternatives && (
        <div className={styles.section}>
          <div className={styles.sectionHead}><span>Other explanations</span></div>
          <ul className={styles.altList}>{edge.alternatives.map((t) => <li key={t}>{t}</li>)}</ul>
        </div>
      )}
      <div className={styles.metaBlock}>
        <div className={styles.metaRow}><span className={styles.metaKey}>Evidence strength</span><ConfidenceDots level={dots} label={strengthLabel} /></div>
        {sources.length ? <SourceList sources={sources} limit={3} onOpen={openAll} /> : <p className={styles.inspBody}>No sources are attached to this link yet.</p>}
        {sources.length > 0 && <Button variant="tertiary" size="sm" icon="file-search" onClick={openAll}>{sources.length > 3 ? `View all ${sources.length} sources` : "View sources"}</Button>}
      </div>
      <div className={styles.safety}><Icon name="info" size={14} /><span>{edge.note ?? "This means these items were related in your records in the way shown above. It does not prove that one caused the other."} Links are not causes, and never a diagnosis.</span></div>
      {canDispute && !disputed && edge.f !== "user" && <Button variant="ghost" full icon="x-circle" onClick={onDispute}>Dispute this connection</Button>}
    </>
  );
}

/* ---------- list / timeline equivalent ---------- */
export function ListView({ clusters, visibleNodes, onSelect, selectedId }: { clusters: Cluster[]; visibleNodes: GraphNode[]; onSelect: (id: string) => void; selectedId: string | null }) {
  const unassigned = visibleNodes.filter((n) => !n.cluster && !n.bridge);
  const groups: Array<{ id: string; label: string; hue: string; href?: string; nodes: GraphNode[] }> = [
    ...clusters.map((c) => ({ id: c.id, label: c.label, hue: c.hue, href: c.href, nodes: visibleNodes.filter((n) => n.cluster === c.id || n.bridge?.includes(c.id)) })),
    { id: "unassigned", label: "Also in your records", hue: NEUTRAL_HUE.hue, nodes: unassigned },
  ];
  return (
    <div className={styles.listView}>
      {groups.map((g) => {
        if (!g.nodes.length) return null;
        return (
          <section key={g.id} className={styles.listSection} aria-label={g.label}>
            <header className={styles.listSectionHead}>
              <span className={styles.clusterDot} style={{ background: g.hue }} />
              <h3 className={styles.listSectionName}>{g.href ? <Link href={g.href}>{g.label}</Link> : g.label}</h3>
              <span className={styles.listSectionMeta}>{plural(g.nodes.length, "item")}</span>
            </header>
            <ul className={styles.listRows}>
              {g.nodes.map((n) => (
                <li key={n.id}><button type="button" className={styles.listRow} data-active={selectedId === n.id || undefined} aria-pressed={selectedId === n.id} onClick={() => onSelect(n.id)}>
                  <span className={styles.listIcon} style={{ color: g.hue }}><Icon name={TYPE_ICON[n.type]} size={15} /></span>
                  <span className={styles.listRowMain}><span className={styles.listRowName}>{n.label}{n.bridge && n.lensRole !== "theory" && <span className={styles.bridgeTag}>bridge</span>}</span><span className={styles.listRowSub}>{typeLabelOf(n)} · {n.ghost ? n.statusNote ?? "open" : `first noted ${n.first}`}</span></span>
                  {n.ghost ? <span className={styles.loopTag}><Icon name="clock" size={12} /> open loop</span> : <ConfidenceDots level={n.conf} label={plural(n.ev, "source")} />}
                </button></li>
              ))}
            </ul>
          </section>
        );
      })}
      {!visibleNodes.length && <p className={styles.inspBody}>Nothing matches the current filters.</p>}
    </div>
  );
}

export function Legend({ lens }: { lens: boolean }) {
  return (
    <div className={styles.legend}>
      <span className={styles.legendGroup}>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="circle" /> Concept</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="diamond" /> Theory / investigation</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="bridge" /> Bridges concerns</span>
        <span className={styles.legendItem}><span className={styles.lShape} data-shape="ghost" /> Open loop</span>
      </span>
      <span className={styles.legendGroup}>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="strong" /> Strong</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="dashed" /> Candidate</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="user" /> You linked</span>
        <span className={styles.legendItem}><span className={styles.lLine} data-kind="conflict" /> Conflicting</span>
        {lens && <span className={styles.legendItem}><span className={styles.lLine} data-kind="for" /> Evidence for / against</span>}
      </span>
    </div>
  );
}
