"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { establishOidcSession } from "@/lib/auth";
import { completeSignIn } from "@/lib/oidc";
import styles from "./EntryScreen.module.css";

/**
 * Completes the ZITADEL Authorization Code + PKCE redirect, then routes by account
 * state: an active account opens the workspace, a new identity starts onboarding.
 * Also serves as the silent-renew iframe target, where it only hands the result
 * back to the parent window.
 */
export function AuthCallback() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const user = await completeSignIn();
        if (!user) return; // silent-renew iframe: the parent window takes over
        const session = await establishOidcSession(user);
        if (active) router.replace(session.onboarded ? "/" : "/onboarding");
      } catch {
        if (active) setError("We couldn't complete sign-in. Please try again.");
      }
    })();
    return () => {
      active = false;
    };
  }, [router]);

  return (
    <div className={styles.screen}>
      <div className={styles.bg} aria-hidden="true" />
      <div className={styles.card}>
        <h1 className={styles.title}>{error ? "Sign-in failed" : "Signing you in…"}</h1>
        {error && (
          <>
            <p className={styles.sub}>{error}</p>
            <div className={styles.options}>
              <button type="button" className={styles.primary} onClick={() => router.replace("/")}>
                <span className={styles.optText}>
                  <b>Back to sign in</b>
                </span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
