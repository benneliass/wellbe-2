"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import {
  devWorkspaceAvailable,
  getSession,
  signInDev,
  signInNewUser,
} from "@/lib/session";
import styles from "./EntryScreen.module.css";

/**
 * The front door (WEL-151 / WEL-181 / WEL-184).
 *
 * Three explicit entry paths, never an auto-login:
 *  1. New to WellBe  -> start onboarding (consent + baseline) into a fresh personal workspace.
 *  2. Continue       -> resume the last signed-in identity (returning user).
 *  3. Dev workspace  -> sign in as the seeded test identity. One selectable workspace,
 *                       clearly labelled, never the default.
 */
export function EntryScreen() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const returning = getSession();
  const hasDev = devWorkspaceAvailable();

  const startNew = () => {
    if (busy) return;
    setBusy(true);
    signInNewUser();
    router.push("/onboarding");
  };

  const continueReturning = () => {
    if (busy || !returning) return;
    setBusy(true);
    router.push(returning.onboarded ? "/" : "/onboarding");
  };

  const enterDev = () => {
    if (busy) return;
    setBusy(true);
    signInDev();
    router.push("/");
  };

  return (
    <div className={styles.screen}>
      <div className={styles.bg} aria-hidden="true" />

      <div className={styles.card}>
        <div className={styles.brandRow}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/wellbe-logo.png" alt="" className={styles.mark} />
          <span className={styles.word}>
            Well<b>Be</b>
          </span>
        </div>

        <h1 className={styles.title}>Your private health workspace</h1>
        <p className={styles.sub}>
          Everything you add stays yours. You decide what is ever shared. Choose how
          you&rsquo;d like to begin.
        </p>

        <div className={styles.options}>
          <button type="button" className={styles.primary} onClick={startNew} disabled={busy}>
            <span className={styles.optIcon}>
              <Icon name="sparkles" size={20} />
            </span>
            <span className={styles.optText}>
              <b>New to WellBe</b>
              <span>Set up your personal workspace</span>
            </span>
            <Icon name="arrow-right" size={18} />
          </button>

          {returning && (
            <button
              type="button"
              className={styles.option}
              onClick={continueReturning}
              disabled={busy}
            >
              <span className={styles.optIcon}>
                <Icon name="user" size={20} />
              </span>
              <span className={styles.optText}>
                <b>Continue{returning.displayName ? ` as ${returning.displayName}` : ""}</b>
                <span>Back to your workspace</span>
              </span>
              <Icon name="arrow-right" size={18} />
            </button>
          )}

          {hasDev && (
            <button
              type="button"
              className={styles.option}
              data-variant="dev"
              onClick={enterDev}
              disabled={busy}
            >
              <span className={styles.optIcon}>
                <Icon name="flask-conical" size={20} />
              </span>
              <span className={styles.optText}>
                <b>Dev workspace</b>
                <span>Sign in to the seeded test data</span>
              </span>
              <span className={styles.tag}>test</span>
            </button>
          )}
        </div>

        <p className={styles.foot}>
          <Icon name="lock" size={13} />
          Only you can see your data. We never sell it.
        </p>
      </div>
    </div>
  );
}
