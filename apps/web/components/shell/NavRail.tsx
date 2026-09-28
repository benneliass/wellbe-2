"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { ProfileModal } from "@/components/account/ProfileModal";
import { SettingsModal } from "@/components/account/SettingsModal";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";
import { PRIMARY_NAV, SECONDARY_NAV, isNavActive, type NavItem } from "@/lib/meta";
import styles from "./NavRail.module.css";

/**
 * Desktop side rail (>= 768px): the five primary destinations, a "More" group
 * for supporting areas, and the workspace switcher. Below 768px the primary
 * destinations move to the BottomNav and this collapses to a slim header whose
 * "More" panel holds the supporting areas and the switcher.
 */
export function NavRail({ onCapture }: { onCapture: () => void }) {
  const pathname = usePathname() ?? "/";
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    setMoreOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!moreOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMoreOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [moreOpen]);

  const renderItem = (item: NavItem) => {
    if (item.action === "capture") {
      return (
        <li key={item.id}>
          <button
            type="button"
            className={styles.item}
            data-capture="true"
            aria-haspopup="dialog"
            onClick={onCapture}
          >
            <Icon name={item.icon} size={19} />
            {item.label}
          </button>
        </li>
      );
    }
    if (item.disabled) {
      return (
        <li key={item.id}>
          <span className={styles.item} data-disabled="true" aria-disabled="true">
            <Icon name={item.icon} size={19} />
            {item.label}
          </span>
        </li>
      );
    }
    const active = isNavActive(item, pathname);
    return (
      <li key={item.id}>
        <Link
          href={item.href}
          className={styles.item}
          data-active={active || undefined}
          aria-current={active ? "page" : undefined}
        >
          <Icon name={item.icon} size={19} />
          {item.label}
        </Link>
      </li>
    );
  };

  return (
    <aside className={styles.rail} data-more-open={moreOpen || undefined}>
      <div className={styles.brand}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.mark} src="/wellbe-mark.png" alt="WellBe" />
        <span className={styles.word}>
          Well<b>Be</b>
        </span>
        <button
          type="button"
          className={styles.moreBtn}
          aria-expanded={moreOpen}
          aria-controls="nav-rail-more"
          onClick={() => setMoreOpen((open) => !open)}
        >
          <Icon name={moreOpen ? "x" : "sliders-horizontal"} size={18} />
          More
        </button>
      </div>

      <nav aria-label="Primary" className={styles.primary}>
        <ul className={styles.list}>{PRIMARY_NAV.map(renderItem)}</ul>
      </nav>

      <div id="nav-rail-more" className={styles.more}>
        <nav aria-label="More" className={styles.secondary}>
          <span className={styles.groupLabel}>More</span>
          <ul className={styles.list}>{SECONDARY_NAV.map(renderItem)}</ul>
        </nav>

        <div className={styles.foot}>
          <div className={styles.privacy}>
            <Icon name="lock" size={14} />
            <span>Only you can see this. You control every share.</span>
          </div>
          <WorkspaceSwitcher
            onOpenProfile={() => setProfileOpen(true)}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        </div>
      </div>

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
    </aside>
  );
}
