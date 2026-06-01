"use client";

import Link from "next/link";
import {
  DisclosureRegion,
  StatePill,
  SourceMarker,
  ReviewMarker,
  type StateToken,
} from "@wellbe/ui";

// Placeholder data. Real data arrives via @wellbe/api-client (WEL-150) + auth (WEL-151).
const THREADS: Array<{
  id: string;
  title: string;
  state: StateToken;
  whatChanged: string;
  nextAction: string;
}> = [
  {
    id: "t-iron",
    title: "Low iron follow-up",
    state: "needs_attention",
    whatChanged: "A repeat ferritin test is due — it was scheduled 3 weeks ago.",
    nextAction: "Book the repeat test",
  },
  {
    id: "t-headache",
    title: "Recurring afternoon headaches",
    state: "watch",
    whatChanged: "You logged 2 new episodes this week.",
    nextAction: "Add what you noticed",
  },
  {
    id: "t-thyroid",
    title: "Thyroid panel",
    state: "stable",
    whatChanged: "Result came back; nothing needs action right now.",
    nextAction: "Review when you like",
  },
];

export default function HomePage() {
  return (
    <main>
      <p style={{ color: "var(--wb-text-muted)", fontSize: "var(--wb-text-sm)", margin: 0 }}>
        Monday
      </p>
      <h1 style={{ fontSize: "var(--wb-text-xl)", marginTop: "var(--wb-space-1)" }}>
        Two things need a look. Everything else is steady.
      </h1>

      <section style={{ marginTop: "var(--wb-space-6)", display: "grid", gap: "var(--wb-space-3)" }}>
        {THREADS.map((t) => (
          <DisclosureRegion
            key={t.id}
            level="L1"
            defaultOpen={false}
            expandLabel="What changed"
            summary={
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--wb-space-2)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--wb-space-2)" }}>
                  <Link href={`/threads/${t.id}`} style={{ fontWeight: 650, textDecoration: "none", color: "var(--wb-text)" }}>
                    {t.title}
                  </Link>
                  <StatePill state={t.state} />
                </div>
                <span style={{ fontSize: "var(--wb-text-sm)", color: "var(--wb-text-muted)" }}>
                  {t.nextAction}
                </span>
              </div>
            }
          >
            <p style={{ margin: 0, fontSize: "var(--wb-text-sm)" }}>{t.whatChanged}</p>
            <div style={{ display: "flex", gap: "var(--wb-space-2)", marginTop: "var(--wb-space-2)", flexWrap: "wrap" }}>
              <SourceMarker count={1} topComponent="c5" />
              <ReviewMarker value="AI-summarized" />
            </div>
          </DisclosureRegion>
        ))}
      </section>

      <p style={{ marginTop: "var(--wb-space-8)", fontSize: "var(--wb-text-xs)", color: "var(--wb-text-muted)" }}>
        Scaffold shell · foundation primitives only · WEL-148
      </p>
    </main>
  );
}
