"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Icon, Modal } from "@wellbe/ui";
import styles from "./TopBar.module.css";

export interface TopBarProps {
  title: string;
  subtitle?: string;
  breadcrumb?: string;
  /** When set, shows a back button linking here. */
  backHref?: string;
}

export function TopBar({ title, subtitle, breadcrumb, backHref }: TopBarProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [notifOpen, setNotifOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = search.trim();
    // Search across your own records is served by Ask WellBe, the one live
    // surface that answers strictly from the user's own data.
    router.push(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask");
  }

  return (
    <header className={styles.top}>
      <div className={styles.lead}>
        {backHref && (
          <Link href={backHref} className={styles.back} aria-label="Back">
            <Icon name="arrow-left" size={18} />
          </Link>
        )}
        <div>
          {breadcrumb && <div className={styles.crumb}>{breadcrumb}</div>}
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <div className={styles.sub}>{subtitle}</div>}
        </div>
      </div>
      <div className={styles.tools}>
        <form className={styles.search} onSubmit={onSearch} role="search">
          <button type="submit" className={styles.searchBtn} aria-label="Search">
            <Icon name="search" size={16} />
          </button>
          <input
            placeholder="Search threads, labs, notes…"
            aria-label="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
        <button
          type="button"
          className={styles.iconbtn}
          title="Notifications"
          aria-label="Notifications"
          aria-haspopup="dialog"
          onClick={() => setNotifOpen(true)}
        >
          <Icon name="bell" size={18} />
          <span className={styles.iconbtnDot} />
        </button>
        <button
          type="button"
          className={styles.iconbtn}
          title="Help"
          aria-label="Help"
          aria-haspopup="dialog"
          onClick={() => setHelpOpen(true)}
        >
          <Icon name="help-circle" size={18} />
        </button>
      </div>

      {notifOpen && <NotificationsModal onClose={() => setNotifOpen(false)} />}
      {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
    </header>
  );
}

/**
 * Notifications surface. There is no push/alert backend yet, so this is honest
 * about that: it points to the two live places where time-sensitive updates
 * actually gather (what-changed digest and open loops) rather than inventing
 * alerts. Calm, never-alarm framing per WellBe's safety posture.
 */
function NotificationsModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal title="Notifications" icon="bell" onClose={onClose}>
      <p style={{ margin: "0 0 16px", color: "var(--fg2)", fontSize: 14, lineHeight: 1.5 }}>
        You&rsquo;re all caught up. WellBe gathers updates calmly in one place rather than
        interrupting you — here&rsquo;s where to look.
      </p>
      <Link href="/delta" className={styles.notifRow} onClick={onClose}>
        <span className={styles.notifIcon}>
          <Icon name="activity" size={18} />
        </span>
        <span className={styles.notifText}>
          <b>What changed</b>
          <span>A source-linked digest of recent updates across your threads.</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </Link>
      <Link href="/workspace" className={styles.notifRow} onClick={onClose}>
        <span className={styles.notifIcon}>
          <Icon name="list" size={18} />
        </span>
        <span className={styles.notifText}>
          <b>Open loops</b>
          <span>Follow-ups and results you&rsquo;re still carrying forward.</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </Link>
    </Modal>
  );
}

/** Quick orientation: what each area does, plus the privacy stance. */
function HelpModal({ onClose }: { onClose: () => void }) {
  const footer = (
    <Button variant="primary" icon="check" onClick={onClose}>
      Got it
    </Button>
  );
  return (
    <Modal title="How WellBe works" icon="help-circle" onClose={onClose} footer={footer}>
      <p style={{ margin: "0 0 14px", color: "var(--fg2)", fontSize: 14, lineHeight: 1.5 }}>
        WellBe helps you understand your own health. Everything is yours, source-linked, and never a
        diagnosis.
      </p>
      <Link href="/workspace" className={styles.notifRow} onClick={onClose}>
        <span className={styles.notifIcon}>
          <Icon name="list" size={18} />
        </span>
        <span className={styles.notifText}>
          <b>Threads</b>
          <span>The concerns you&rsquo;re carrying forward, with what changed.</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </Link>
      <Link href="/ask" className={styles.notifRow} onClick={onClose}>
        <span className={styles.notifIcon}>
          <Icon name="message-circle" size={18} />
        </span>
        <span className={styles.notifText}>
          <b>Ask WellBe</b>
          <span>Ask a question — answered only from your own records.</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </Link>
      <Link href="/prepare" className={styles.notifRow} onClick={onClose}>
        <span className={styles.notifIcon}>
          <Icon name="user" size={18} />
        </span>
        <span className={styles.notifText}>
          <b>Prepare for a visit</b>
          <span>Build a one-page, source-linked packet you control and can share.</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </Link>
      <div className={styles.helpPrivacy}>
        <Icon name="lock" size={14} />
        <span>Only you can see your data. Every share is your decision and revocable.</span>
      </div>
    </Modal>
  );
}
