"use client";

import { useState, type FormEvent } from "react";
import { Icon } from "@wellbe/ui";
import { beginSignIn } from "@/lib/oidc";
import type { PasswordRules, SignInResult } from "@/lib/server/zitadel-login";
import styles from "./EntryScreen.module.css";

type Step = "credentials" | "change" | "expired";

const MESSAGES: Partial<Record<SignInResult["kind"] | "network", string>> = {
  invalid_credentials: "That login name and password don't match. Please try again.",
  locked: "This login is locked after too many attempts. Ask your WellBe admin to unlock it.",
  unavailable: "Sign-in is unavailable right now. Please try again in a moment.",
  network: "Couldn't reach WellBe. Check your connection and try again.",
  weak_password: "That password doesn't meet the requirements below.",
};

export function describeRules(rules: PasswordRules | null): string[] {
  if (!rules) return [];
  const out: string[] = [];
  if (rules.minLength > 0) out.push(`At least ${rules.minLength} characters`);
  if (rules.requiresUppercase) out.push("An uppercase letter");
  if (rules.requiresLowercase) out.push("A lowercase letter");
  if (rules.requiresNumber) out.push("A number");
  if (rules.requiresSymbol) out.push("A symbol");
  return out;
}

async function submit(body: Record<string, string>): Promise<SignInResult | { kind: "network" }> {
  try {
    const res = await fetch("/login/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    const data = (await res.json()) as SignInResult;
    return data && typeof data.kind === "string" ? data : { kind: "unavailable" };
  } catch {
    return { kind: "network" };
  }
}

/**
 * WellBe's own sign-in card (ZITADEL login V2 base URI = the web origin, so
 * authorize requests land on /login?authRequest=V2_…). ZITADEL still checks the
 * password and issues the tokens; see lib/server/zitadel-login.ts.
 */
export function LoginScreen({ authRequestId }: { authRequestId: string | null }) {
  const [step, setStep] = useState<Step>(authRequestId ? "credentials" : "expired");
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rules, setRules] = useState<PasswordRules | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = (result: SignInResult | { kind: "network" }) => {
    switch (result.kind) {
      case "ok":
        window.location.assign(result.callbackUrl);
        return;
      case "password_change_required":
        setRules(result.rules);
        setStep("change");
        setBusy(false);
        return;
      case "weak_password":
        setRules(result.rules);
        break;
      case "expired":
        setStep("expired");
        setBusy(false);
        return;
      case "invalid_credentials":
        setPassword("");
        break;
    }
    setError(MESSAGES[result.kind] ?? MESSAGES.unavailable!);
    setBusy(false);
  };

  const onCredentials = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || !authRequestId) return;
    setBusy(true);
    setError(null);
    handle(await submit({ authRequestId, loginName, password }));
  };

  const onChange = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || !authRequestId) return;
    if (newPassword !== confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setBusy(true);
    setError(null);
    handle(await submit({ authRequestId, loginName, password, newPassword }));
  };

  const restart = async () => {
    setBusy(true);
    try {
      await beginSignIn();
    } catch {
      setError(MESSAGES.network!);
      setBusy(false);
    }
  };

  const ruleList = describeRules(rules);

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

        {step === "credentials" && (
          <>
            <h1 className={styles.title}>Sign in to WellBe</h1>
            <p className={styles.sub}>Your private health workspace. Only you can see your data.</p>
            <form className={styles.form} onSubmit={onCredentials} noValidate>
              <label className={styles.field}>
                <span className={styles.label}>Email or username</span>
                <input
                  className={styles.input}
                  name="username"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  required
                  autoFocus
                  value={loginName}
                  onChange={(e) => setLoginName(e.target.value)}
                />
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Password</span>
                <span className={styles.inputWrap}>
                  <input
                    className={styles.input}
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className={styles.reveal}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    <Icon name="eye" size={16} />
                  </button>
                </span>
              </label>
              {error && (
                <p className={styles.error} role="alert">
                  <Icon name="alert-circle" size={14} />
                  {error}
                </p>
              )}
              <button
                type="submit"
                className={styles.submit}
                disabled={busy || !loginName.trim() || !password}
              >
                {busy ? "Signing in…" : "Sign in"}
                {!busy && <Icon name="arrow-right" size={18} />}
              </button>
            </form>
            <p className={styles.hint}>Forgot your password? Your WellBe admin can reset it.</p>
          </>
        )}

        {step === "change" && (
          <>
            <h1 className={styles.title}>Choose a new password</h1>
            <p className={styles.sub}>
              Your temporary password has to be replaced before you continue.
            </p>
            <form className={styles.form} onSubmit={onChange} noValidate>
              <input type="hidden" name="username" autoComplete="username" value={loginName} />
              <label className={styles.field}>
                <span className={styles.label}>New password</span>
                <input
                  className={styles.input}
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  autoFocus
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Confirm new password</span>
                <input
                  className={styles.input}
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </label>
              {ruleList.length > 0 && (
                <ul className={styles.rules} aria-label="Password requirements">
                  {ruleList.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {error && (
                <p className={styles.error} role="alert">
                  <Icon name="alert-circle" size={14} />
                  {error}
                </p>
              )}
              <button
                type="submit"
                className={styles.submit}
                disabled={busy || !newPassword || !confirm}
              >
                {busy ? "Saving…" : "Save and continue"}
                {!busy && <Icon name="arrow-right" size={18} />}
              </button>
            </form>
          </>
        )}

        {step === "expired" && (
          <>
            <h1 className={styles.title}>Let&rsquo;s start again</h1>
            <p className={styles.sub}>
              This sign-in link has expired or was already used.
            </p>
            {error && (
              <p className={styles.error} role="alert">
                <Icon name="alert-circle" size={14} />
                {error}
              </p>
            )}
            <button type="button" className={styles.submit} onClick={restart} disabled={busy}>
              Sign in
              <Icon name="arrow-right" size={18} />
            </button>
          </>
        )}

        <p className={styles.foot}>
          <Icon name="lock" size={13} />
          Only you can see your data. We never sell it.
        </p>
      </div>
    </div>
  );
}
