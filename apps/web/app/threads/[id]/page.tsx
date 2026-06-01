"use client";

import Link from "next/link";
import { use } from "react";
import {
  DisclosureRegion,
  StatePill,
  SourceMarker,
  ReviewMarker,
  ConfidenceMeter,
} from "@wellbe/ui";

const STAGES = ["Started", "Open", "In motion", "Needs attention", "Understood", "Closed"];

export default function ThreadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const currentStage = "In motion";

  return (
    <main>
      <Link href="/" style={{ fontSize: "var(--wb-text-sm)", textDecoration: "none" }}>
        ← Home
      </Link>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "var(--wb-space-3)", gap: "var(--wb-space-2)" }}>
        <h1 style={{ fontSize: "var(--wb-text-lg)" }}>Low iron follow-up</h1>
        <StatePill state="needs_attention" />
      </div>

      {/* Journey Rail (WEL-139) — compact placeholder */}
      <ol
        aria-label="Journey"
        style={{ display: "flex", gap: "var(--wb-space-2)", listStyle: "none", padding: 0, marginTop: "var(--wb-space-4)", flexWrap: "wrap" }}
      >
        {STAGES.map((stage) => {
          const active = stage === currentStage;
          return (
            <li
              key={stage}
              aria-current={active ? "step" : undefined}
              style={{
                fontSize: "var(--wb-text-xs)",
                padding: "2px var(--wb-space-2)",
                borderRadius: "999px",
                border: "1px solid var(--wb-border)",
                background: active ? "var(--wb-accent)" : "var(--wb-surface)",
                color: active ? "var(--wb-accent-contrast)" : "var(--wb-text-muted)",
                fontWeight: active ? 650 : 400,
              }}
            >
              {stage}
            </li>
          );
        })}
      </ol>

      <section style={{ marginTop: "var(--wb-space-6)", display: "grid", gap: "var(--wb-space-3)" }}>
        <DisclosureRegion
          level="L1"
          defaultOpen
          summary={<h2 style={{ fontSize: "var(--wb-text-base)" }}>Your story</h2>}
        >
          <blockquote
            style={{
              margin: 0,
              paddingLeft: "var(--wb-space-3)",
              borderLeft: "3px solid var(--wb-accent)",
              fontFamily: "var(--wb-font-serif)",
            }}
          >
            “I&apos;ve felt wiped out since the spring, even after sleeping well.”
          </blockquote>
          <div style={{ marginTop: "var(--wb-space-2)" }}>
            <ReviewMarker value="patient-entered" />
          </div>
        </DisclosureRegion>

        <DisclosureRegion
          level="L3"
          summary={<h2 style={{ fontSize: "var(--wb-text-base)" }}>What WellBe noticed</h2>}
          expandLabel="Show evidence"
        >
          <p style={{ margin: 0, fontSize: "var(--wb-text-sm)" }}>
            Your last ferritin was on the low side, and a repeat test was planned but not yet done.
          </p>
          <div style={{ display: "flex", gap: "var(--wb-space-2)", marginTop: "var(--wb-space-2)", flexWrap: "wrap" }}>
            <SourceMarker count={2} />
            <ReviewMarker value="AI-summarized" />
            <ConfidenceMeter level="moderate" basis="based on 2 prior results" />
          </div>
        </DisclosureRegion>
      </section>

      <p style={{ marginTop: "var(--wb-space-8)", fontSize: "var(--wb-text-xs)", color: "var(--wb-text-muted)" }}>
        Thread {id} · scaffold shell · WEL-148
      </p>
    </main>
  );
}
