"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Icon, Modal } from "@wellbe/ui";
import { ProfileModal } from "@/components/account/ProfileModal";
import { SettingsModal } from "@/components/account/SettingsModal";
import { useAccount } from "@/lib/account";
import { NotificationBell } from "./NotificationBell";
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
  const [helpOpen, setHelpOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const account = useAccount();

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
        <NotificationBell />
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
        <button
          type="button"
          className={styles.avatarBtn}
          title={account.email ?? account.name}
          aria-label={`Your account: ${account.name}`}
          aria-haspopup="dialog"
          onClick={() => setProfileOpen(true)}
        >
          {account.initials}
        </button>
      </div>

      {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
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
    </header>
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
      <p style={{ margin: "0 0 14px", color: "var(--fg2)", fontSize: "var(--text-body)", lineHeight: "var(--lh-normal)" }}>
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
