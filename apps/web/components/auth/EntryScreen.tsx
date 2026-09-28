"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { demoSignInAvailable, isOidcMode, oidcConfigured } from "@/lib/auth-config";
import { beginSignIn } from "@/lib/oidc";
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
 * Dev mode offers three explicit entry paths, never an auto-login:
 *  1. New to WellBe  -> start onboarding (consent + baseline) into a fresh personal workspace.
 *  2. Continue       -> resume the last signed-in identity (returning user).
 *  3. Dev workspace  -> sign in as the seeded test identity. One selectable workspace,
 *                       clearly labelled, never the default.
 *
 * OIDC mode replaces them with a single ZITADEL sign-in (accounts are provisioned
 * in ZITADEL, not self-registered); the callback routes an identity with no
 * WellBe account yet into onboarding. When the server enables it, "Try the demo"
 * goes through the same redirect and /login opens the shared demo workspace.
 */
export function EntryScreen() {
  return isOidcMode() ? <OidcEntryScreen /> : <DevEntryScreen />;
}

function OidcEntryScreen() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(
    oidcConfigured() ? null : "Sign-in isn't configured for this deployment yet.",
  );

  const signIn = async (demo = false) => {
    if (busy || !oidcConfigured()) return;
    setBusy(true);
    setError(null);
    try {
      await beginSignIn(demo ? { demo: true } : undefined);
    } catch {
      setError("Couldn't reach the sign-in service. Please try again.");
      setBusy(false);
    }
  };

  return (
    <div className={styles.screen}>
      <div className={styles.bg} aria-hidden="true" />

      <div className={styles.card}>
        <div className={styles.brandRow}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/wellbe-mark.png" alt="" className={styles.mark} />
          <span className={styles.word}>
            Well<b>Be</b>
          </span>
        </div>

        <h1 className={styles.title}>Your private health workspace</h1>
        <p className={styles.sub}>
          Everything you add stays yours. You decide what is ever shared.
        </p>

        <div className={styles.options}>
          <button
            type="button"
            className={styles.primary}
            onClick={() => signIn()}
            disabled={busy || !oidcConfigured()}
          >
            <span className={styles.optIcon}>
              <Icon name="user" size={20} />
            </span>
            <span className={styles.optText}>
              <b>Sign in</b>
              <span>Continue to your workspace</span>
            </span>
            <Icon name="arrow-right" size={18} />
          </button>

          {demoSignInAvailable() && (
            <button
              type="button"
              className={styles.option}
              data-variant="demo"
              onClick={() => signIn(true)}
              disabled={busy}
            >
              <span className={styles.optIcon}>
                <Icon name="sparkles" size={20} />
              </span>
              <span className={styles.optText}>
                <b>Try the demo</b>
                <span>Sample data, shared with every visitor</span>
              </span>
              <span className={styles.tag}>shared</span>
            </button>
          )}
        </div>

        {error && (
          <p className={styles.sub} role="alert">
            {error}
          </p>
        )}

        <p className={styles.foot}>
          <Icon name="lock" size={13} />
          Only you can see your data. We never sell it.
        </p>
      </div>
    </div>
  );
}

function DevEntryScreen() {
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
          <img src="/wellbe-mark.png" alt="" className={styles.mark} />
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
