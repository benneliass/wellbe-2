"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { ProfileModal } from "@/components/account/ProfileModal";
import { SettingsModal } from "@/components/account/SettingsModal";
import { SignalsPanel } from "./SignalsPanel";
import { LAUNCH_ACTIONS, type LaunchAction } from "@/lib/meta";
import styles from "./Launcher.module.css";

/** The calm front door. "Full View" and most actions lead into the workspace. */
export function Launcher() {
  const router = useRouter();
  const [captureOpen, setCaptureOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [askValue, setAskValue] = useState("");

  const goFullView = () => router.push("/workspace");

  const onAction = (action: LaunchAction) => {
    if (action.id === "log") {
      setCaptureOpen(true);
      return;
    }
    if (action.href) router.push(action.href);
  };

  const onAsk = (e: React.FormEvent) => {
    e.preventDefault();
    const q = askValue.trim();
    router.push(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask");
  };

  return (
    <div className={styles.launch}>
      <div className={styles.bg} aria-hidden="true" />

      <header className={styles.top}>
        <button type="button" className={styles.brand} onClick={goFullView} aria-label="WellBe">
          <span className={styles.wordmark}>
            Well<b>Be</b>
          </span>
        </button>
        <SignalsPanel />
        <div className={styles.topright}>
          <button type="button" className={styles.full} onClick={goFullView}>
            Full View <Icon name="arrow-right" size={16} />
          </button>
          <button
            type="button"
            className={styles.avatar}
            onClick={() => setProfileOpen(true)}
            aria-label="Your account"
            aria-haspopup="dialog"
          >
            A<span className={styles.avatarDot} />
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.hero}>
          <div className={styles.orb}>
            <div className={styles.orbRings} aria-hidden="true" />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/wellbe-logo.png" alt="" className={styles.orbImg} />
          </div>
          <h1 className={styles.h1}>
            What do you need <em>today?</em>
          </h1>
          <p className={styles.sub}>We&rsquo;ll guide you to the right things.</p>
        </div>

        <div className={styles.rec}>
          {/* Every pill shares the calm teal treatment: red is reserved for
              Safety Gate-approved urgent guidance, never a launcher entry point. */}
          <div className={styles.recRow}>
            {LAUNCH_ACTIONS.map((a) => (
              <button key={a.id} type="button" className={styles.pill} onClick={() => onAction(a)}>
                <span className={styles.pillIcon}>
                  <Icon name={a.icon} size={22} />
                </span>
                <span className={styles.pillTitle}>{a.title}</span>
                <span className={styles.pillSub}>{a.sub}</span>
              </button>
            ))}
          </div>
        </div>

        <div className={styles.or}>
          <span>OR</span>
        </div>
        <form className={styles.ask} onSubmit={onAsk}>
          <span className={styles.askLead}>
            <Icon name="activity" size={20} />
          </span>
          <input
            placeholder="Type what you need…"
            aria-label="Ask WellBe"
            value={askValue}
            onChange={(e) => setAskValue(e.target.value)}
          />
          <button type="submit" className={styles.askGo} aria-label="Go">
            <Icon name="arrow-right" size={18} />
          </button>
        </form>

        <div className={styles.foot}>
          <Icon name="lock" size={14} />
          Your data is private and secure. We never sell your data.
        </div>
      </main>

      <button
        type="button"
        className={styles.settings}
        title="Settings"
        aria-label="Settings"
        aria-haspopup="dialog"
        onClick={() => setSettingsOpen(true)}
      >
        <Icon name="sliders-horizontal" size={20} />
      </button>

      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
      {profileOpen && (
        <ProfileModal
          onClose={() => setProfileOpen(false)}
          onOpenSettings={() => {
            setProfileOpen(false);
            setSettingsOpen(true);
          }}
        />
      )}
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
