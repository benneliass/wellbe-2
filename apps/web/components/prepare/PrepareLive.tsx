"use client";

import { useRef, useState } from "react";
import { Button, Icon } from "@wellbe/ui";
import { getApiClient } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import { useThreads } from "@/lib/hooks";
import { StateNote } from "@/components/placeholder/StateNote";
import { PacketReview } from "./PacketReview";
import { PacketShareStep } from "./PacketShareStep";
import { PacketStepper, type PacketStep } from "./PacketStepper";
import type { VisitPacket } from "./packetFormat";
import styles from "./PrepareLive.module.css";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * The visit packet as a 3-step, preview-first flow: Choose -> Review -> Share.
 * Nothing leaves WellBe until the person approves the preview and creates a link.
 */
export function PrepareLive() {
  const signedIn = Boolean(useSession()?.patientId);
  const threadsQuery = useThreads();
  const [step, setStep] = useState<PacketStep>("choose");
  const [approved, setApproved] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [questions, setQuestions] = useState("");
  const [goals, setGoals] = useState("");
  const [packet, setPacket] = useState<VisitPacket | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const headingRef = useRef<HTMLDivElement>(null);

  if (!signedIn && threadsQuery.isError) {
    return (
      <StateNote
        icon="lock"
        title="Sign in to prepare a packet"
        description="Once you're signed in, you can build a source-linked packet from your threads."
      />
    );
  }

  const threads = threadsQuery.data ?? [];
  const reachable = new Set<PacketStep>(["choose"]);
  if (packet) reachable.add("review");
  if (packet && approved) reachable.add("share");

  function goTo(next: PacketStep) {
    setStep(next);
    headingRef.current?.focus();
  }

  function toggleThread(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleGenerate() {
    setError(null);
    setBusy(true);
    try {
      const { data, error: apiError } = await getApiClient().POST("/v2/visit-packets", {
        body: {
          title: "Visit packet",
          thread_ids: Array.from(selected),
          include_summary: true,
          prep: {
            questions: splitLines(questions),
            goals: splitLines(goals),
            observations: [],
          },
        },
      });
      if (apiError || !data) throw new Error("Couldn't build the packet. Please try again.");
      setPacket({ ...data, statements: data.statements ?? [] });
      setApproved(false);
      goTo("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong building the packet.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatement(id: string, included: boolean) {
    if (!packet) return;
    const previous = packet;
    setReviewError(null);
    setApproved(false);
    setPacket({
      ...packet,
      statements: (packet.statements ?? []).map((s) =>
        s.statement_id === id ? { ...s, included } : s,
      ),
    });
    const { error: apiError } = await getApiClient().PATCH("/v2/visit-packets/{packet_id}", {
      params: { path: { packet_id: packet.packet_id } },
      body: { inclusions: [{ statement_id: id, included }] },
    });
    if (apiError) {
      setPacket(previous);
      setReviewError("That change couldn't be saved. Please try again.");
    }
  }

  async function editStatement(id: string, text: string) {
    if (!packet) return;
    const { data, error: apiError } = await getApiClient().PATCH("/v2/visit-packets/{packet_id}", {
      params: { path: { packet_id: packet.packet_id } },
      body: { edits: [{ statement_id: id, text }] },
    });
    if (apiError || !data) throw new Error("That change couldn't be saved. Please try again.");
    setApproved(false);
    setPacket({ ...data, statements: data.statements ?? [] });
  }

  return (
    <div className={styles.wrap}>
      <PacketStepper current={step} reachable={reachable} onSelect={goTo} />
      <div ref={headingRef} tabIndex={-1} className={styles.focusAnchor} aria-live="polite">
        <span className={styles.srOnly}>
          {step === "choose" ? "Step 1, Choose" : step === "review" ? "Step 2, Review" : "Step 3, Share"}
        </span>
      </div>

      {step === "choose" && (
        <div>
          <p className={styles.intro}>
            Build a one-page, source-linked packet for an upcoming visit. Pick the concerns to
            include and add what you want to raise — you preview and approve everything before any
            sharing.
          </p>

          <div className={styles.section}>
            <div className={styles.sectionHead}>Concerns to include</div>
            {threadsQuery.isLoading ? (
              <p className={styles.muted}>Loading your threads…</p>
            ) : threads.length === 0 ? (
              <p className={styles.muted}>
                No threads yet. You can still add questions and goals below.
              </p>
            ) : (
              <div className={styles.threadList}>
                {threads.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={styles.threadRow}
                    aria-pressed={selected.has(t.id)}
                    data-on={selected.has(t.id) || undefined}
                    onClick={() => toggleThread(t.id)}
                  >
                    <span className={styles.check} data-on={selected.has(t.id) || undefined}>
                      {selected.has(t.id) && <Icon name="check" size={12} />}
                    </span>
                    <span className={styles.threadTitle}>{t.title}</span>
                  </button>
                ))}
              </div>
            )}
            <p className={styles.hintLine}>Leave all unchecked to include every active concern.</p>
          </div>

          <div className={styles.section}>
            <label htmlFor="prep-questions" className={styles.sectionHead}>
              Questions you want to ask
            </label>
            <textarea
              id="prep-questions"
              className={styles.textarea}
              placeholder="One question per line…"
              value={questions}
              onChange={(e) => setQuestions(e.target.value)}
            />
          </div>

          <div className={styles.section}>
            <label htmlFor="prep-goals" className={styles.sectionHead}>
              Your goals for the visit
            </label>
            <textarea
              id="prep-goals"
              className={styles.textarea}
              placeholder="One goal per line…"
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
            />
          </div>

          {error && (
            <p className={styles.error} role="alert">
              <Icon name="alert-circle" size={14} /> {error}
            </p>
          )}

          <div className={styles.stepFoot}>
            {packet && (
              <Button variant="tertiary" onClick={() => goTo("review")} disabled={busy}>
                Keep current preview
              </Button>
            )}
            <Button variant="primary" icon="sparkles" onClick={handleGenerate} disabled={busy}>
              {busy ? "Building…" : packet ? "Rebuild packet" : "Build packet"}
            </Button>
          </div>
          {packet && (
            <p className={styles.hintLine}>
              Rebuilding makes a fresh preview from these choices; your current preview stays
              unshared.
            </p>
          )}
        </div>
      )}

      {step === "review" && packet && (
        <>
          {reviewError && (
            <p className={styles.error} role="alert">
              <Icon name="alert-circle" size={14} /> {reviewError}
            </p>
          )}
          <PacketReview
            packet={packet}
            onToggle={toggleStatement}
            onEdit={editStatement}
            onBack={() => goTo("choose")}
            onContinue={() => {
              setApproved(true);
              goTo("share");
            }}
          />
        </>
      )}

      {step === "share" && packet && approved && (
        <PacketShareStep packet={packet} onBack={() => goTo("review")} />
      )}
    </div>
  );
}
