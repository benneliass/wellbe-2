"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { LAUNCH_ACTIONS } from "@/lib/meta";
import styles from "./Launcher.module.css";

/** The calm front door. "Full View" and most actions lead into the workspace. */
export function Launcher() {
  const router = useRouter();
  const [captureOpen, setCaptureOpen] = useState(false);

  const goFullView = () => router.push("/workspace");

  const onAction = (id: string) => {
    if (id === "log") {
      setCaptureOpen(true);
    } else if (id === "triage") {
      router.push("/threads/labs");
    } else {
      router.push("/workspace");
    }
  };

  return (
    <div className={styles.launch}>
      <div className={styles.bg} aria-hidden="true" />

      <header className={styles.top}>
        <button type="button" className={styles.brand} onClick={goFullView}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/wellbe-logo.png" alt="WellBe" />
          <span>
            Well<b>Be</b>
          </span>
        </button>
        <div className={styles.topright}>
          <button type="button" className={styles.full} onClick={goFullView}>
            Full View <Icon name="arrow-right" size={16} />
          </button>
          <button type="button" className={styles.avatar}>
            A<span className={styles.avatarDot} />
          </button>
        </div>
      </header>

      <div className={styles.sync}>
        <span className={styles.syncDot} />
        Data synced <span className={styles.syncTime}>4 min ago</span>
      </div>

      <button type="button" className={styles.signals} onClick={goFullView}>
        <span className={styles.signalsIcon}>
          <Icon name="activity" size={20} />
        </span>
        <span className={styles.signalsText}>
          <b>Your signals look steady</b>
          <span>6 of 6 systems in range</span>
        </span>
        <Icon name="chevron-down" size={18} className={styles.signalsChev} />
      </button>

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
        <div className={styles.recRow}>
          {LAUNCH_ACTIONS.map((a) => (
            <button
              key={a.id}
              type="button"
              className={`${styles.pill} ${a.tone === "alert" ? styles.pillAlert : ""}`}
              onClick={() => onAction(a.id)}
            >
              {a.tone === "alert" && <span className={styles.pillDot} />}
              <span className={styles.pillIcon}>
                <Icon name={a.icon} size={22} />
              </span>
              <span className={styles.pillTitle}>{a.title}</span>
              <span className={`${styles.pillSub} ${a.tone === "alert" ? styles.pillSubAlert : ""}`}>
                {a.sub}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className={styles.or}>
        <span>OR</span>
      </div>
      <form
        className={styles.ask}
        onSubmit={(e) => {
          e.preventDefault();
          goFullView();
        }}
      >
        <span className={styles.askLead}>
          <Icon name="activity" size={20} />
        </span>
        <input placeholder="Type what you need…" aria-label="Ask WellBe" />
        <button type="submit" className={styles.askGo} aria-label="Go">
          <Icon name="arrow-right" size={18} />
        </button>
      </form>

      <div className={styles.foot}>
        <Icon name="lock" size={14} />
        Your data is private and secure. We never sell your data.
      </div>

      <button type="button" className={styles.settings} title="Settings" aria-label="Settings">
        <Icon name="sliders-horizontal" size={20} />
      </button>

      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
    </div>
  );
}
