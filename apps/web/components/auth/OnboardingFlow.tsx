"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { clearSession, updateSession } from "@/lib/session";
import { useSession } from "@/lib/useSession";
import styles from "./OnboardingFlow.module.css";

type OnboardingState = components["schemas"]["OnboardingStateV1"];

type Step = "welcome" | "consent" | "baseline" | "finalizing";

/**
 * Authenticate-first onboarding (WEL-181). The session already carries the
 * federated identity; this flow captures explicit core consent and a minimal,
 * skippable baseline, then finalizes — which provisions the personal workspace
 * and is idempotent, so a refresh mid-flow never double-creates anything.
 */
export function OnboardingFlow() {
  const router = useRouter();
  const session = useSession();
  const [step, setStep] = useState<Step>("welcome");
  const [state, setState] = useState<OnboardingState | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [goals, setGoals] = useState("");
  const [error, setError] = useState<string | null>(null);

  // No session at all -> the user reached onboarding without a front-door choice.
  useEffect(() => {
    if (session === null) router.replace("/");
    else if (session?.onboarded) router.replace("/");
  }, [session, router]);

  // Open (or resume) the pending onboarding draft to load the core-consent set.
  useEffect(() => {
    if (!session || session.onboarded) return;
    let active = true;
    (async () => {
      try {
        const { data } = await getApiClient().POST("/v1/onboarding/start", { body: {} });
        if (active && data) setState(data);
      } catch {
        if (active) setError("Couldn't start onboarding. Please try again.");
      }
    })();
    return () => {
      active = false;
    };
  }, [session]);

  async function finalize() {
    if (!accepted) return;
    setStep("finalizing");
    setError(null);
    try {
      const { data, error: apiError } = await getApiClient().POST("/v1/onboarding/finalize", {
        body: {
          accept_core_consent: true,
          baseline: { display_name: displayName.trim() || null, goals: goals.trim() || null },
        },
      });
      if (apiError || !data || data.status !== "active") {
        throw new Error("finalize_failed");
      }
      updateSession({
        patientId: data.controller_patient_id ?? null,
        onboarded: true,
        displayName: displayName.trim() || data.display_name || null,
      });
      router.replace("/workspace");
    } catch {
      setError("Couldn't finish setting up your workspace. Please try again.");
      setStep("baseline");
    }
  }

  function cancel() {
    clearSession();
    router.replace("/");
  }

  const consent = state?.core_consent ?? [];

  return (
    <div className={styles.screen}>
      <div className={styles.bg} aria-hidden="true" />
      <div className={styles.card}>
        <div className={styles.steps} aria-hidden="true">
          {(["welcome", "consent", "baseline"] as Step[]).map((s) => (
            <span key={s} className={styles.dot} data-on={stepIndex(step) >= stepIndex(s) || undefined} />
          ))}
        </div>

        {step === "welcome" && (
          <>
            <h1 className={styles.title}>Welcome to WellBe</h1>
            <p className={styles.sub}>
              This is your private space to keep track of your health over time. You stay
              in control of everything — nothing is ever shared unless you choose to.
            </p>
            <ul className={styles.points}>
              <li>
                <Icon name="lock" size={16} /> Your data belongs to you
              </li>
              <li>
                <Icon name="shield-check" size={16} /> Source-linked, never a diagnosis
              </li>
              <li>
                <Icon name="user" size={16} /> You decide every share, and can undo it
              </li>
            </ul>
            <div className={styles.actions}>
              <button type="button" className={styles.ghost} onClick={cancel}>
                Not now
              </button>
              <button type="button" className={styles.primary} onClick={() => setStep("consent")}>
                Get started <Icon name="arrow-right" size={16} />
              </button>
            </div>
          </>
        )}

        {step === "consent" && (
          <>
            <h1 className={styles.title}>What WellBe will do for you</h1>
            <p className={styles.sub}>
              To set up your personal workspace, WellBe needs your okay for these core
              things. That&rsquo;s all for now — anything beyond this, we&rsquo;ll always ask
              you at the moment it matters.
            </p>
            <ul className={styles.consentList}>
              {consent.map((c) => (
                <li key={c.purpose} className={styles.consentItem}>
                  <Icon name="check-circle-2" size={18} className={styles.consentIcon} />
                  <span>{c.label}</span>
                </li>
              ))}
            </ul>
            <label className={styles.agree}>
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
              />
              <span>I understand and agree to these core purposes.</span>
            </label>
            <div className={styles.actions}>
              <button type="button" className={styles.ghost} onClick={() => setStep("welcome")}>
                Back
              </button>
              <button
                type="button"
                className={styles.primary}
                disabled={!accepted}
                onClick={() => setStep("baseline")}
              >
                Continue <Icon name="arrow-right" size={16} />
              </button>
            </div>
          </>
        )}

        {(step === "baseline" || step === "finalizing") && (
          <>
            <h1 className={styles.title}>A little about you</h1>
            <p className={styles.sub}>
              Optional — you can skip this and add it later. Nothing here is required to
              start.
            </p>
            <label className={styles.field}>
              <span>What should we call you?</span>
              <input
                type="text"
                placeholder="Your name (optional)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={step === "finalizing"}
              />
            </label>
            <label className={styles.field}>
              <span>What do you hope WellBe helps with?</span>
              <textarea
                placeholder="e.g. keep track of my symptoms before appointments (optional)"
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
                disabled={step === "finalizing"}
              />
            </label>
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.ghost}
                onClick={() => setStep("consent")}
                disabled={step === "finalizing"}
              >
                Back
              </button>
              <button
                type="button"
                className={styles.primary}
                onClick={finalize}
                disabled={step === "finalizing" || !accepted}
              >
                {step === "finalizing" ? "Setting up…" : "Finish setup"}
                {step !== "finalizing" && <Icon name="check" size={16} />}
              </button>
            </div>
          </>
        )}

        <p className={styles.foot}>
          <Icon name="lock" size={13} />
          Your private workspace. Only you can see it.
        </p>
      </div>
    </div>
  );
}

function stepIndex(step: Step): number {
  return { welcome: 0, consent: 1, baseline: 2, finalizing: 2 }[step];
}
