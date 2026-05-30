import { useState } from "react";
import {
  H1, H2, H3, Text, Card, CardHeader, CardBody, Grid, Row, Stack,
  Pill, Stat, Callout, Divider, CollapsibleSection,
  useHostTheme, colorPalette,
} from "cursor/canvas";

// ─── Data: Alignment Map (Research A–E) ───────────────────────────────────────

const VERDICT_ITEMS = [
  { area: "Longitudinal memory — Principle 5", verdict: "Confirmed", pillTone: "success" as const, note: "Research B/C/D all independently document that temporal disconnection is the direct cause of harm." },
  { area: "Context Is Everything — Principle 3", verdict: "Confirmed", pillTone: "success" as const, note: "The normal-test trap is the most recurring failure mode across all 5 packages. Decontextualized results cause documented diagnostic harm." },
  { area: "M22 Concern Tracker", verdict: "Confirmed", pillTone: "success" as const, note: "Research C: 'simply receiving/viewing/filing a result is not enough.' Ownership vacuum is the #1 finding." },
  { area: "doctor-summary feature", verdict: "Confirmed", pillTone: "success" as const, note: "Research D's list of what clinicians need earlier reads almost as a feature spec." },
  { area: "User Narrative Primacy — Principle 11", verdict: "Confirmed", pillTone: "success" as const, note: "Research C: patient language ('dismissed', 'still no idea') maps to concrete process failures. Patient voice is diagnostic signal." },
  { area: "M14 Missing Data Detection", verdict: "Confirmed", pillTone: "success" as const, note: "Research B identifies 'what the test cannot rule out' as a critical surfacing failure — validated across all five packages." },
  { area: "investigation-triage flow", verdict: "Needs Extension", pillTone: "warning" as const, note: "Good for pre-visit. Research A+B show the black zone is post-encounter: pending results lost, safety-net forgotten, referrals vanished." },
  { area: "Pattern Detection — M11", verdict: "Needs Extension", pillTone: "warning" as const, note: "Correlation detection validated but insufficient. Research demands typed diagnostic episodes with resolution state, not just surfaced signals." },
  { area: "Patient data → changed clinical outcomes", verdict: "Challenged", pillTone: "deleted" as const, note: "Research C: patient voice is systematically overridden by clinical authority even when correct. A better-structured summary fed to a dismissive clinician doesn't change the dismissal dynamic." },
  { area: "Compounding Intelligence timeline", verdict: "Challenged", pillTone: "deleted" as const, note: "Month 12 / Year 3 power assumes sustained engagement. Consumer health apps rarely achieve this without strong re-engagement mechanisms." },
  { area: "Closed-loop result ownership", verdict: "Critical Gap", pillTone: "deleted" as const, note: "Not in 33 modules. Research B: 9 case rows. Research F: strongly supported (LI-004). Every stream converges here." },
  { area: "Diagnostic Episode as persistent entity", verdict: "Critical Gap", pillTone: "deleted" as const, note: "Pattern detection finds correlations; it doesn't maintain a thread accumulating across visits, tests, referrals with open/closed resolution status." },
  { area: "Full referral lifecycle tracking", verdict: "Critical Gap", pillTone: "deleted" as const, note: "doctor-discovery treats referral as a single event. Research A + Research F (LI-005) show it's 6+ steps, each a failure point." },
  { area: "Post-encounter continuity layer", verdict: "Opportunity", pillTone: "info" as const, note: "Research A+B converge: most failures happen after the first encounter. Research F confirms (LI-009: pending-test discharge contract)." },
  { area: "Pre-consultation intake (B2B2C)", verdict: "Opportunity", pillTone: "info" as const, note: "Research D implies WellBe could be the structured pre-visit intake layer sold to practices. Research F: rich patient intake timeline (LI-002)." },
  { area: "Patient-held record for fragmented systems", verdict: "Opportunity", pillTone: "info" as const, note: "Research E + Research F (LI-019): patient-held records work across system types where formal records don't travel." },
];

const CONFIRMED = VERDICT_ITEMS.filter((v) => v.verdict === "Confirmed");
const NEEDS = VERDICT_ITEMS.filter((v) => v.verdict === "Needs Extension");
const CHALLENGED = VERDICT_ITEMS.filter((v) => v.verdict === "Challenged");
const GAPS = VERDICT_ITEMS.filter((v) => v.verdict === "Critical Gap");
const OPPORTUNITIES = VERDICT_ITEMS.filter((v) => v.verdict === "Opportunity");

// ─── Data: Cross-cutting insights ─────────────────────────────────────────────

const CROSS_CUTS = [
  {
    id: "thesis", label: "Core thesis validated — and bounded", tag: "Validated & Bounded", pillTone: "neutral" as const,
    body: "'No one connected the dots' is the most documented failure mode across all 5 research packages independently, and Research F elevates it to LI-001 (strongly supported). But the failure also happens between clinical actors — handoff, discharge, referral completion — where the patient is absent and patient-side data alone doesn't reach the actors who can act.",
    bullets: ["M22 Concern Tracker and longitudinal memory are correctly prioritized", "Impact is real but bounded to patient-side advocacy without clinician-side connectivity", "The 33-module architecture has no mechanism to enforce closed-loop follow-through"],
  },
  {
    id: "blackzone", label: "The post-encounter black zone is the real opportunity", tag: "Opportunity", pillTone: "info" as const,
    body: "Research A+B converge independently: most diagnostic failures happen after the first encounter. Research F maps this to 14 specific patient journey failure stages, and names the pending-test discharge contract (LI-009) as strongly supported. WellBe's current vision ends at 'prepare for your visit.'",
    bullets: ["investigation-triage needs a post-visit mode covering discharge, results, safety-net", "Pending-test discharge contract: what's pending, who owns it, when to expect it, what to do if no contact", "Month 12 compounding value shifts from personal insight to systemic continuity"],
  },
  {
    id: "ownership", label: "Ownership vacuum is the single highest-frequency failure", tag: "Critical Gap", pillTone: "deleted" as const,
    body: "Every research stream independently converges: abnormal results, referrals, and unresolved symptoms fail because no named person owns them with a deadline and escalation path. Research B: 9 case rows. Research F: LI-004 (strongly supported) with guardrail: risk-ranked worklist, escalation by criticality, backup owner, patient notification only with pathway to explanation.",
    bullets: ["An Abnormal Result Ownership Ledger should be elevated to a core product primitive", "M22 Concern Tracker holds concerns but doesn't enforce ownership with deadlines and escalation", "Every concern: owner, deadline, patient-visible status, escalation trigger, audit of overdue closures"],
  },
];

// ─── Data: Research F Feature Backlog ─────────────────────────────────────────

const FEATURES_STRONG = [
  { id: "LI-001", name: "Diagnostic episode layer / unresolved-problem tracker", users: "Doctor · Nurse · Patient · Specialist", risk: "High", guardrail: "Every issue has status, owner, next action, uncertainty statement, clinician override; monitor false positives." },
  { id: "LI-002", name: "Rich patient intake timeline with change-from-baseline", users: "Patient · Caregiver · Nurse · Doctor", risk: "Medium", guardrail: "Adaptive short form; plain language; translation; caregiver mode; separate patient narrative from clinician assessment." },
  { id: "LI-003", name: "Repeat-visit diagnostic reset trigger", users: "Doctor · Nurse · Urgent care · ED", risk: "High", guardrail: "Trigger only on meaningful persistence/worsening/repeat count; require clinician acknowledgment and override rationale." },
  { id: "LI-004", name: "Closed-loop abnormal result ownership ledger", users: "Doctor · Nurse · Admin · Patient · Specialist", risk: "High", guardrail: "Risk-ranked worklist; escalation by criticality; backup owner; patient notification only with pathway to explanation; audit overdue." },
  { id: "LI-005", name: "Referral completion and transparency tracker", users: "Doctor · Patient · Admin · Specialist", risk: "High", guardrail: "Separate 'no pathway', 'more info needed', 'wrong service', 'clinical advice only', 'diagnosis ruled out'; follow-up owner for advice-only." },
  { id: "LI-006", name: "Normal-test trap explainer and persistent-symptom safety net", users: "Doctor · Nurse · Patient", risk: "High", guardrail: "Use uncertainty language; show what remains unexplained; avoid automatic diagnosis; tie to clinician-reviewed safety net." },
  { id: "LI-007", name: "Patient voice protection: verbatim concern + correction path", users: "Patient · Caregiver · Doctor", risk: "Medium", guardrail: "Separate patient voice from clinical assessment; respectful language normalization; patient-visible summary corrections." },
  { id: "LI-009", name: "Doctor-facing concise timeline and red-flag summary", users: "Doctor · Nurse · Specialist", risk: "High", guardrail: "Show source links, timestamps, uncertainty, missing data; flag generated summary as support only." },
  { id: "LI-010", name: "Triage red-flag co-pilot with reassessment timers", users: "Nurse · ED staff", risk: "High", guardrail: "Support nurse judgment; calibrated timers; monitor over-alerting." },
  { id: "LI-014", name: "Pending-test discharge contract", users: "Patient · Doctor · Nurse · Admin", risk: "High", guardrail: "'What is pending,' 'when you will hear,' 'who owns it,' 'what to do if no contact' — plain language throughout." },
  { id: "LI-025", name: "Patient/family deterioration escalation route", users: "Patient · Caregiver · Nurse · Doctor", risk: "High", guardrail: "Clear criteria, named response team, acknowledgment timestamp, triage of escalation requests, respectful language." },
];

const FEATURES_SOME = [
  { id: "LI-008", name: "Concern-by-concern visit closure", users: "Doctor · Patient · Nurse", risk: "Medium", guardrail: "Allow 'deferred with plan' disposition; keep closure concise; prioritize safety-critical unresolved concerns." },
  { id: "LI-011", name: "Missing-data checklist (family history, medication access, prior tests)", users: "Patient · Caregiver · Doctor", risk: "Medium", guardrail: "Optional patient-controlled disclosure; privacy notices; clinician confirms before action; no blame for non-adherence." },
  { id: "LI-013", name: "Lab trend and personal-baseline explorer", users: "Doctor · Patient", risk: "High", guardrail: "Clinical validation before alerts; avoid anxiety loops from visualization alone." },
  { id: "LI-015", name: "Cross-specialty pattern map", users: "Doctor · Specialist · Patient", risk: "High", guardrail: "Local referral directory; 'consider asking' prompts, not automated referral; shared summary with clinical question." },
  { id: "LI-022", name: "Medication and access-as-diagnostic-clue capture", users: "Patient · Doctor · Nurse", risk: "Med-High", guardrail: "Ask nonjudgmentally; patient-controlled sensitive data; link to assistance/referral; do not equate cost barriers with noncompliance." },
  { id: "LI-023", name: "Note-diff and copied-forward detection", users: "Doctor · Specialist · Safety reviewer", risk: "Med-High", guardrail: "Prioritize clinically meaningful changes; allow clinician dismissal; tie to unresolved episode summary." },
  { id: "LI-026", name: "Diagnosis-status clarity in patient portal", users: "Patient · Doctor · Admin", risk: "Med-High", guardrail: "Clinician-authored uncertainty templates; explain status categories; show who to contact and when." },
];

const FEATURES_REGIONAL = [
  { id: "LI-016", name: "Waiting-room / pre-triage deterioration check-in", region: "High-volume EDs", guardrail: "Escalation button always visible; distinguish symptom worsening from new presentation." },
  { id: "LI-019", name: "Patient-held record and out-of-system care import", region: "Low-resource / cross-border", guardrail: "Provenance labels; clinician verification; patient consent; data-quality confidence; do not overwrite official results." },
  { id: "LI-020", name: "Language, interpreter and cultural-safety layer", region: "Migrant / multilingual settings", guardrail: "Connect to actual interpreter workflows; track completion not just need; avoid ethnicity-based risk scoring." },
  { id: "LI-021", name: "CHW and informal-provider referral capture mode", region: "Sub-Saharan Africa / South Asia / rural", guardrail: "Protocol-bound scope, supervision, offline mode, referral confirmation, local-language prompts." },
  { id: "LI-018", name: "Low-resource diagnostic availability and stockout-aware plan", region: "Low-resource clinics", guardrail: "Offline/paper/SMS modes; aggregate stockout reporting; no punitive clinician metrics for stockouts." },
];

const FEATURES_CAUTION = [
  { id: "LI-024", name: "Workload-aware alert management and risk-ranked worklists", issue: "More alerts can worsen the exact overload that causes missed results and poor follow-up.", guardrail: "Actionable, tiered alerts; suppress duplicates; ownership + escalation; measure false positives/negatives." },
  { id: "LI-902", name: "More alerts for every possible missed diagnosis", issue: "Alert overload is itself a documented safety risk (Research D, E001/Q003).", guardrail: "Risk-ranked, actionable, owned worklists are safer than more pop-ups. Needs threshold and workload studies." },
];

const FEATURES_CONTRADICTED = [
  { id: "LI-900", name: "One universal workflow for all countries/settings", finding: "Contradicted by evidence — care-flow models differ by gatekeeper, open-access, CHW-based, fragmented public/private." },
  { id: "LI-901", name: "Pure single-symptom digital triage as diagnostic front door", finding: "Contradicted by evidence — single-symptom routes lose complexity and prior high-risk history (Research D: E007/Q005)." },
  { id: "unsafe", name: "Autonomous diagnosis without clinician review", finding: "Unsafe — explicitly named in Research F unsupported features. Never converts AI pattern to final diagnostic claim." },
];

// ─── Data: Black Zone Map (14 stages) ─────────────────────────────────────────

const BLACK_ZONES = [
  { stage: "Before visit", failure: "Access barriers, informal/private care, persistent symptoms or high-risk history never enter stable diagnostic pathway.", prevention: "Patient-held record import; access-barrier fields; CHW/informal referral capture; incomplete-workup registry." },
  { stage: "Arrival / registration", failure: "Repeat visit, family history, referral note or deterioration not visible before triage.", prevention: "Front-door repeat-visit banner; referral-note visibility; arrival-to-assessment timer; family/caregiver concern field." },
  { stage: "Intake form / digital triage", failure: "Single-symptom routing loses complexity, prior cancer/high-risk history, or patient meaning.", prevention: "Hybrid intake: multi-symptom, free text, prior-history auto-pull, human-review escape hatch." },
  { stage: "Nurse triage / vitals", failure: "Abnormal vitals, repeat visits and red flags lose salience under cognitive strain.", prevention: "Triage co-pilot, repeat-vital timers, deterioration check-in, acuity + diagnostic-uncertainty view." },
  { stage: "First clinician assessment", failure: "First plausible diagnosis or mental-health/age/gender label closes inquiry.", prevention: "Diagnostic time-out: dangerous-to-miss alternatives, bias/misattribution guardrail, patient quote visible." },
  { stage: "Medical history", failure: "Family history, medication access, patient theory, functional impact and prior test context not integrated.", prevention: "Risk-context checklist and structured timeline with patient/caregiver input." },
  { stage: "Physical exam", failure: "Time-sensitive exams absent or delayed; telehealth gap hides required in-person exam.", prevention: "Complaint-linked exam checklist; telehealth-to-in-person conversion criteria; pathway timers." },
  { stage: "Labs / imaging ordered", failure: "Wrong test, no test, stockout, or wrong imaging scope.", prevention: "Order-set suggestions; imaging-scope warning; unavailable-test alternate plan; resource availability capture." },
  { stage: "Lab / imaging interpretation", failure: "Abnormal result exists but is not communicated, acknowledged or acted on.", prevention: "Result/finding lifecycle tracker, owner/deadline, critical semantics, patient notification status." },
  { stage: "Diagnosis discussion / discharge", failure: "Uncertainty, pending tests and unresolved symptoms disappear from patient plan.", prevention: "Concern-by-concern closure; 'what remains unexplained'; pending-test contract; specific safety-net." },
  { stage: "Referral", failure: "Referral delayed, wrong, rejected, advice-only or never completed.", prevention: "Referral status taxonomy and completion tracker with next owner at each step." },
  { stage: "Follow-up / repeat visit", failure: "Return visits do not cause diagnostic reset.", prevention: "Repeat-visit diagnostic reset and symptom-still-present check-ins with persistence threshold." },
  { stage: "Specialist review", failure: "Specialist sees one slice, wrong chart, remote note, or wrong specialty.", prevention: "Cross-specialty summary pane, identity verification, clinical question and unresolved-pattern map." },
  { stage: "Long-term monitoring", failure: "Slow trends and chronic invalidation hide deterioration.", prevention: "Trend explorer, functional status, quality-of-life, unresolved-problem registry." },
];

// ─── Data: Research F Product Principles ──────────────────────────────────────

const RF_PRINCIPLES = [
  "Support clinician judgment; do not replace it.",
  "Make patient narratives easier to capture, preserve, and review.",
  "Track unresolved symptoms, repeat visits, abnormal results, and referrals over time.",
  "Keep summaries concise and explain why a signal is highlighted.",
  "Reduce documentation burden and alert fatigue.",
  "Preserve uncertainty and avoid final diagnostic claims.",
  "Build for regional and resource differences.",
  "Require safety governance for high-risk flags, bias risks, false positives, and false negatives.",
];

const DO_NOT_DIAGNOSE = [
  "Do not provide final diagnoses.",
  "Do not tell a patient they definitely have or do not have a condition.",
  "Do not overrule clinician judgment.",
  "Do not hide uncertainty.",
  "Do not convert weak evidence into strong recommendations.",
  "Always route high-risk concerns to clinician review or setting-appropriate urgent-care instructions.",
];

// ─── Data: Strategic Recs ─────────────────────────────────────────────────────

const RECS_CONFIRM = [
  "M22 Concern Tracker — add named deadline + patient-visible status + escalation trigger (Research F LI-004 guardrail)",
  "doctor-summary — Research D + Research F LI-009 read as a feature spec; build it",
  "Temporal engines M11/M12 — ensure outputs persist as typed episodes with resolution state (LI-001)",
  "User Narrative Primacy — structured verbatim capture + patient correction path (LI-007)",
  "M14 Missing Data — especially normal-test-trap variant: 'what this test cannot rule out' (LI-006)",
];

const RECS_ADD = [
  "Closed-loop result ownership ledger — owner, deadline, escalation, patient-visible resolution (LI-004, CRITICAL)",
  "Diagnostic Episode as persistent entity — accumulates across years; distinct from pattern detection (LI-001, CRITICAL)",
  "Full referral lifecycle tracker — 6+ steps, each with status and owner (LI-005, CRITICAL)",
  "Post-encounter continuity mode — pending-test discharge contract, safety-net documentation (LI-009, CRITICAL)",
  "Repeat-visit diagnostic reset trigger — on meaningful persistence/worsening/count (LI-003, HIGH)",
  "Patient-held record import — photos, PDFs, SMS, manual entry for pre-WellBe and out-of-system history (LI-019, HIGH)",
  "Patient/family deterioration escalation route — named response team, acknowledgment timestamp (LI-025, HIGH)",
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function WellBeSynthesis() {
  const theme = useHostTheme();
  const [bzFilter, setBzFilter] = useState<"all" | "early" | "mid" | "late">("all");

  const rowStyle = { padding: "10px 12px", borderRadius: 6, background: theme.fill.tertiary };
  const accentArrow = { color: theme.accent.primary, flexShrink: 0 as const, fontSize: 13 };

  const filteredZones = bzFilter === "all" ? BLACK_ZONES
    : bzFilter === "early" ? BLACK_ZONES.slice(0, 4)
    : bzFilter === "mid" ? BLACK_ZONES.slice(4, 9)
    : BLACK_ZONES.slice(9);

  return (
    <Stack gap={40} style={{ padding: 32, maxWidth: 1100, margin: "0 auto" }}>

      {/* ── Header ── */}
      <Stack gap={10}>
        <Text size="small" tone="tertiary" weight="medium">
          6-research synthesis · Research A–F · 164+ sources · WellBe overview doc · 2026-05-30
        </Text>
        <H1>WellBe × Research: Full Analysis</H1>
        <Text tone="secondary" style={{ maxWidth: 720, lineHeight: 1.6 }}>
          Four agents analyzed WellBe's vision against Research A–E (missed signals, patient complaints, clinician pain points, patient flows, global health systems). Research F (Product Design Synthesis) adds 26 living insights, 25+ evidence-graded features, 14-stage black zone map, safety governance, and contradicted approaches — all synthesized below.
        </Text>
      </Stack>

      {/* ── Vision Guardrail ── */}
      <Callout tone="info">
        <Stack gap={6}>
          <Text weight="semibold" style={{ fontSize: 13 }}>Vision guardrail — read before interpreting the analysis below</Text>
          <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.65 }}>
            WellBe is a <strong>personal</strong> health intelligence system. The primary user is always the individual. The research studied systemic clinical failures — that is context, not a product spec. When the research describes a gap in the clinical system (ownership vacuums, referral voids, handoff failures), WellBe's answer is to <strong>empower the patient within that system</strong>, not to become the system. Insights labelled "Opportunity" or "Vision Shift" that suggest clinician-facing tools or B2B2C pivots are hypothetical design spaces, not priorities. The comparison engine — cross-time, cross-source synthesis — is WellBe's moat, but it is a mechanism serving personal understanding, not the product identity.
          </Text>
        </Stack>
      </Callout>

      {/* ── Summary Stats ── */}
      <Grid columns={4} gap={12}>
        <Card><CardBody>
          <Stat label="Validations" value="12" tone="success" />
          <Text size="small" tone="tertiary">10 strong · 2 moderate</Text>
        </CardBody></Card>
        <Card><CardBody>
          <Stat label="Challenges" value="10" tone="danger" />
          <Text size="small" tone="tertiary">3 fundamental · 5 significant</Text>
        </CardBody></Card>
        <Card><CardBody>
          <Stat label="Design Gaps" value="12" tone="warning" />
          <Text size="small" tone="tertiary">4 critical · 5 high · 3 medium</Text>
        </CardBody></Card>
        <Card><CardBody>
          <Stat label="Research F Features" value="26" tone="info" />
          <Text size="small" tone="tertiary">Living insights with evidence status</Text>
        </CardBody></Card>
      </Grid>

      <Divider />

      {/* ── Cross-cutting insights (A–E) ── */}
      <Stack gap={20}>
        <Stack gap={4}>
          <H2>Three Cross-Cutting Insights</H2>
          <Text tone="secondary" size="small">Findings that appeared independently across multiple agents without coordination — now further confirmed by Research F.</Text>
        </Stack>
        {CROSS_CUTS.map((insight) => (
          <Card key={insight.id}>
            <CardHeader trailing={<Pill tone={insight.pillTone}>{insight.tag}</Pill>}>{insight.label}</CardHeader>
            <CardBody>
              <Stack gap={14}>
                <Text tone="secondary" style={{ lineHeight: 1.65, fontSize: 13 }}>{insight.body}</Text>
                <Stack gap={6}>
                  {insight.bullets.map((b, i) => (
                    <Row key={i} gap={10} align="start">
                      <Text style={accentArrow}>→</Text>
                      <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{b}</Text>
                    </Row>
                  ))}
                </Stack>
              </Stack>
            </CardBody>
          </Card>
        ))}
      </Stack>

      <Divider />

      {/* ── Vision Alignment Map (A–E) ── */}
      <Stack gap={20}>
        <Stack gap={4}>
          <H2>Vision Alignment Map</H2>
          <Text tone="secondary" size="small">Every major WellBe module, principle, or feature assessed against Research A–E. Research F references added where they reinforce or sharpen the verdict.</Text>
        </Stack>

        {([
          { title: "Strongly Confirmed", count: CONFIRMED.length, trailing: <Pill tone="success" size="sm">Research directly validates</Pill>, items: CONFIRMED, label: "Validated" },
          { title: "Needs Extension", count: NEEDS.length, trailing: <Pill tone="warning" size="sm">Right direction, incomplete</Pill>, items: NEEDS, label: "Extend" },
          { title: "Challenged by Research", count: CHALLENGED.length, trailing: <Pill tone="deleted" size="sm">Research complicates the assumption</Pill>, items: CHALLENGED, label: "Challenged" },
          { title: "Critical Gaps", count: GAPS.length, trailing: <Pill tone="deleted" size="sm">Missing; highest-frequency failure in research</Pill>, items: GAPS, label: "Gap" },
          { title: "Emergent Opportunities", count: OPPORTUNITIES.length, trailing: <Pill tone="info" size="sm">Research-grounded vision shifts</Pill>, items: OPPORTUNITIES, label: "Opportunity" },
        ] as const).map((section) => (
          <CollapsibleSection key={section.title} title={section.title} count={section.count} trailing={section.trailing} defaultOpen>
            <Stack gap={6}>
              {section.items.map((item) => (
                <Row key={item.area} gap={14} align="start" style={rowStyle}>
                  <Stack gap={2} style={{ flex: "0 0 200px" }}>
                    <Text weight="medium" style={{ fontSize: 13 }}>{item.area}</Text>
                    <Pill size="sm" tone={item.pillTone}>{section.label}</Pill>
                  </Stack>
                  <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.55 }}>{item.note}</Text>
                </Row>
              ))}
            </Stack>
          </CollapsibleSection>
        ))}
      </Stack>

      <Divider />

      {/* ── Research F: Evidence-Graded Feature Backlog ── */}
      <Stack gap={20}>
        <Stack gap={4}>
          <H2>Research F — Evidence-Graded Feature Backlog</H2>
          <Text tone="secondary" size="small">
            Research F synthesized all 5 prior packages into 26 living insights (LI-001–LI-026) plus 3 contradicted approaches. Every feature has a status, evidence chain, risk level, and guardrail.
          </Text>
        </Stack>

        <CollapsibleSection title="Strongly Supported" count={FEATURES_STRONG.length} trailing={<Pill tone="success" size="sm">Build these</Pill>} defaultOpen>
          <Stack gap={6}>
            {FEATURES_STRONG.map((f) => (
              <Row key={f.id} gap={14} align="start" style={rowStyle}>
                <Stack gap={2} style={{ flex: "0 0 48px" }}>
                  <Text weight="medium" style={{ fontSize: 11, color: theme.text.tertiary }}>{f.id}</Text>
                  <Pill size="sm" tone={f.risk === "High" ? "deleted" : "warning"}>{f.risk}</Pill>
                </Stack>
                <Stack gap={3} style={{ flex: 1 }}>
                  <Text weight="medium" style={{ fontSize: 13 }}>{f.name}</Text>
                  <Text size="small" tone="tertiary">Users: {f.users}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>Guardrail: {f.guardrail}</Text>
                </Stack>
              </Row>
            ))}
          </Stack>
        </CollapsibleSection>

        <CollapsibleSection title="Supported by Some Evidence" count={FEATURES_SOME.length} trailing={<Pill tone="warning" size="sm">Build with monitoring</Pill>} defaultOpen>
          <Stack gap={6}>
            {FEATURES_SOME.map((f) => (
              <Row key={f.id} gap={14} align="start" style={rowStyle}>
                <Stack gap={2} style={{ flex: "0 0 48px" }}>
                  <Text weight="medium" style={{ fontSize: 11, color: theme.text.tertiary }}>{f.id}</Text>
                  <Pill size="sm" tone="warning">{f.risk}</Pill>
                </Stack>
                <Stack gap={3} style={{ flex: 1 }}>
                  <Text weight="medium" style={{ fontSize: 13 }}>{f.name}</Text>
                  <Text size="small" tone="tertiary">Users: {f.users}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>Guardrail: {f.guardrail}</Text>
                </Stack>
              </Row>
            ))}
          </Stack>
        </CollapsibleSection>

        <CollapsibleSection title="Region-Specific" count={FEATURES_REGIONAL.length} trailing={<Pill tone="info" size="sm">Configure for context</Pill>} defaultOpen={false}>
          <Stack gap={6}>
            {FEATURES_REGIONAL.map((f) => (
              <Row key={f.id} gap={14} align="start" style={rowStyle}>
                <Stack gap={2} style={{ flex: "0 0 48px" }}>
                  <Text weight="medium" style={{ fontSize: 11, color: theme.text.tertiary }}>{f.id}</Text>
                  <Pill size="sm" tone="info">Regional</Pill>
                </Stack>
                <Stack gap={3} style={{ flex: 1 }}>
                  <Text weight="medium" style={{ fontSize: 13 }}>{f.name}</Text>
                  <Text size="small" tone="tertiary">Applies to: {f.region}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>Guardrail: {f.guardrail}</Text>
                </Stack>
              </Row>
            ))}
          </Stack>
        </CollapsibleSection>

        <CollapsibleSection title="Needs Caution / Unsafe Without Guardrails" count={FEATURES_CAUTION.length} trailing={<Pill tone="deleted" size="sm">Design carefully</Pill>} defaultOpen>
          <Stack gap={6}>
            {FEATURES_CAUTION.map((f) => (
              <Row key={f.id} gap={14} align="start" style={rowStyle}>
                <Stack gap={2} style={{ flex: "0 0 48px" }}>
                  <Text weight="medium" style={{ fontSize: 11, color: theme.text.tertiary }}>{f.id}</Text>
                  <Pill size="sm" tone="deleted">Caution</Pill>
                </Stack>
                <Stack gap={3} style={{ flex: 1 }}>
                  <Text weight="medium" style={{ fontSize: 13 }}>{f.name}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>Issue: {f.issue}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>Guardrail: {f.guardrail}</Text>
                </Stack>
              </Row>
            ))}
          </Stack>
        </CollapsibleSection>

        <CollapsibleSection title="Contradicted by Evidence" count={FEATURES_CONTRADICTED.length} trailing={<Pill tone="deleted" size="sm">Do not build as described</Pill>} defaultOpen>
          <Stack gap={6}>
            {FEATURES_CONTRADICTED.map((f) => (
              <Row key={f.id} gap={14} align="start" style={rowStyle}>
                <Stack gap={2} style={{ flex: "0 0 48px" }}>
                  <Text weight="medium" style={{ fontSize: 11, color: theme.text.tertiary }}>{f.id}</Text>
                  <Pill size="sm" tone="deleted">Contradicted</Pill>
                </Stack>
                <Stack gap={3} style={{ flex: 1 }}>
                  <Text weight="medium" style={{ fontSize: 13 }}>{f.name}</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>{f.finding}</Text>
                </Stack>
              </Row>
            ))}
          </Stack>
        </CollapsibleSection>
      </Stack>

      <Divider />

      {/* ── Research F: Black Zone Map ── */}
      <Stack gap={16}>
        <Stack gap={4}>
          <H2>Research F — Black Zone Map</H2>
          <Text tone="secondary" size="small">14 patient journey stages where diagnostic failures concentrate. Research F maps each to a product prevention mechanism and guardrail.</Text>
        </Stack>

        <Row gap={8} wrap>
          {(["all", "early", "mid", "late"] as const).map((f) => (
            <Pill key={f} active={bzFilter === f} onClick={() => setBzFilter(f)}>
              {f === "all" ? "All stages" : f === "early" ? "Before visit → Vitals" : f === "mid" ? "Assessment → Discharge" : "Referral → Long-term"}
            </Pill>
          ))}
        </Row>

        <Stack gap={6}>
          {filteredZones.map((bz, i) => (
            <Row key={i} gap={14} align="start" style={rowStyle}>
              <Stack gap={2} style={{ flex: "0 0 160px" }}>
                <Text weight="medium" style={{ fontSize: 12 }}>{bz.stage}</Text>
                <Pill size="sm" tone="deleted">Black Zone</Pill>
              </Stack>
              <Stack gap={4} style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{bz.failure}</Text>
                <Row gap={8} align="start">
                  <Text style={{ ...accentArrow, fontSize: 12 }}>→</Text>
                  <Text size="small" tone="secondary" style={{ lineHeight: 1.5 }}>{bz.prevention}</Text>
                </Row>
              </Stack>
            </Row>
          ))}
        </Stack>
      </Stack>

      <Divider />

      {/* ── Research F: Product Principles + Safety Rules ── */}
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Research F — Product Principles</CardHeader>
          <CardBody>
            <Stack gap={8}>
              {RF_PRINCIPLES.map((p, i) => (
                <Row key={i} gap={10} align="start">
                  <Text style={{ color: theme.text.tertiary, flexShrink: 0, fontSize: 13 }}>{i + 1}.</Text>
                  <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{p}</Text>
                </Row>
              ))}
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="deleted" size="sm">Hard limits</Pill>}>Do-Not-Diagnose Rules</CardHeader>
          <CardBody>
            <Stack gap={8}>
              {DO_NOT_DIAGNOSE.map((r, i) => (
                <Row key={i} gap={10} align="start">
                  <Text style={{ color: colorPalette.orange, flexShrink: 0, fontSize: 13, fontWeight: 600 }}>✗</Text>
                  <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{r}</Text>
                </Row>
              ))}
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Divider />

      {/* ── The Honest Tension ── */}
      <Stack gap={16}>
        <H2>The Honest Tension</H2>
        <Grid columns={2} gap={16}>
          <Stack gap={8}>
            <H3>What WellBe solves well</H3>
            <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.65 }}>
              The patient returning for the 4th visit. The one whose symptoms are dismissed. The one who can't articulate what's different about this episode. WellBe gives them longitudinal memory, structured narrative, pattern evidence, and a clinician-ready summary. The research documents exactly this failure mode 32+ times across 5 packages, and Research F elevates it to 11 strongly-supported features.
            </Text>
          </Stack>
          <Stack gap={8}>
            <H3>What WellBe can't solve alone</H3>
            <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.65 }}>
              The referral placed but never completed. The abnormal result filed but never followed up. The shift-change handoff where critical context is lost. These happen between clinical actors while the patient is absent. No patient-side data closes these loops without clinician-side connectivity. Research F names this the diagnostic episode layer gap (LI-001).
            </Text>
          </Stack>
        </Grid>
        <Callout tone="warning" title="The scope boundary the research draws">
          WellBe makes patients more informed and more capable of self-advocacy within a system that will still push back. That is a real and meaningful value proposition — but narrower than the current vision implies. The research consistently shows the failure is systemic, not informational. Research F's safety rules add: never convert weak evidence into strong recommendations, and preserve uncertainty in every output.
        </Callout>
      </Stack>

      <Divider />

      {/* ── Strategic Recommendations ── */}
      <Stack gap={20}>
        <H2>Strategic Recommendations</H2>
        <Grid columns={2} gap={16}>
          <Card>
            <CardHeader>Confirm & Accelerate</CardHeader>
            <CardBody>
              <Stack gap={10}>
                {RECS_CONFIRM.map((item, i) => (
                  <Row key={i} gap={10} align="start">
                    <Text style={{ color: colorPalette.green, flexShrink: 0, fontSize: 13, fontWeight: 600 }}>✓</Text>
                    <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{item}</Text>
                  </Row>
                ))}
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Add Urgently — Critical Gaps</CardHeader>
            <CardBody>
              <Stack gap={10}>
                {RECS_ADD.map((item, i) => (
                  <Row key={i} gap={10} align="start">
                    <Text style={{ color: colorPalette.orange, flexShrink: 0, fontSize: 13, fontWeight: 600 }}>!</Text>
                    <Text style={{ fontSize: 13, lineHeight: 1.5 }}>{item}</Text>
                  </Row>
                ))}
              </Stack>
            </CardBody>
          </Card>
        </Grid>

        <Stack gap={10}>
          <H3>Research-Suggested Directions — Scoped Against Vision Guardrail</H3>
          <Callout tone="warning">
            <Text style={{ fontSize: 13, lineHeight: 1.6 }}>
              The two directions below surfaced strongly in the research but are <strong>outside the current personal vision</strong> unless explicitly decided otherwise. They are documented here for transparency — not as recommendations.
            </Text>
          </Callout>
          <Card collapsible>
            <CardHeader trailing={<Pill tone="deleted" size="sm">Out of scope</Pill>}>Clinician-as-second-user / continuity infrastructure</CardHeader>
            <CardBody>
              <Stack gap={10}>
                <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.65 }}>
                  Research A–E + Research F's 14-stage black zone map frame the clinical system's problem as "nothing stays connected across actors, time, and system boundaries." The research-implied response is: build the connective tissue — clinicians as a second user class, post-encounter as the primary surface, a B2B2C platform sold to practices. This is a coherent product, but it is not WellBe's vision.
                </Text>
                <Callout tone="success">
                  <Text style={{ fontSize: 13, lineHeight: 1.6 }}>
                    <strong>The personal-first reframe:</strong> Every black-zone failure point maps to something the <em>user</em> needs to track, remember, and advocate for. Post-encounter continuity is fully achievable as a personal tool — the user keeps the longitudinal thread, follows up on pending results, tracks referral status, owns what's unresolved. No clinician login required.
                  </Text>
                </Callout>
              </Stack>
            </CardBody>
          </Card>
          <Card collapsible>
            <CardHeader trailing={<Pill tone="deleted" size="sm">Out of scope</Pill>}>B2B2C pre-consultation intake sold to practices</CardHeader>
            <CardBody>
              <Stack gap={10}>
                <Text tone="secondary" style={{ fontSize: 13, lineHeight: 1.65 }}>
                  Research D + Research F (LI-002) suggest WellBe could become a structured pre-consultation intake layer ordered by clinicians and delivered to patients before appointments — making WellBe mission-critical to practices rather than to individuals. This creates strong institutional lock-in and potential revenue moats.
                </Text>
                <Callout tone="success">
                  <Text style={{ fontSize: 13, lineHeight: 1.6 }}>
                    <strong>The personal-first reframe:</strong> The doctor-summary feature already covers this — the user generates a structured summary (symptom in own words → timeline → medications + prior tests → patient theory) and <em>chooses to share it</em> with their clinician. The value accrues to the individual first. If practices adopt it as intake, that's a distribution channel, not the product identity.
                  </Text>
                </Callout>
              </Stack>
            </CardBody>
          </Card>
        </Stack>
      </Stack>

      {/* ── Footer ── */}
      <Stack gap={4} style={{ borderTop: `1px solid ${theme.stroke.tertiary}`, paddingTop: 20 }}>
        <Text size="small" tone="tertiary">
          Research A (Health System Patient Flows, 56 sources) · Research B (Missed Signals, 15 sources) · Research C (Patient Complaints, 39 sources) · Research D (Clinician Pain Points, 24 sources) · Research E (Global Health, 30 sources) · Research F (Product Design Synthesis, 26 living insights, 164+ consolidated sources)
        </Text>
        <Text size="small" tone="tertiary">Synthesized 2026-05-30 · WellBe overview doc last synthesized 2026-05-30</Text>
      </Stack>

    </Stack>
  );
}
