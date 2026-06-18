"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { ProfileModal } from "@/components/account/ProfileModal";
import { SettingsModal } from "@/components/account/SettingsModal";
import { NAV_ITEMS, type NavItem } from "@/lib/meta";
import styles from "./NavRail.module.css";

function isActive(item: NavItem, pathname: string): boolean {
  if (item.href === "#") return false;
  if (item.id === "threads") return pathname.startsWith("/workspace") || pathname.startsWith("/threads");
  if (item.href === "/") return pathname === "/";
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function NavRail({ onCapture }: { onCapture: () => void }) {
  const pathname = usePathname();
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <aside className={styles.rail}>
      <div className={styles.brand}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.mark} src="/wellbe-logo.png" alt="WellBe" />
        <span className={styles.word}>
          Well<b>Be</b>
        </span>
      </div>

      <button type="button" className={styles.capture} onClick={onCapture}>
        <Icon name="plus" size={18} />
        Capture
      </button>

      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item, pathname);
          if (item.disabled) {
            return (
              <span key={item.id} className={styles.item} data-disabled="true" aria-disabled="true">
                <Icon name={item.icon} size={19} />
                {item.label}
              </span>
            );
          }
          return (
            <Link key={item.id} href={item.href} className={styles.item} data-active={active || undefined}>
              <Icon name={item.icon} size={19} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className={styles.foot}>
        <div className={styles.privacy}>
          <Icon name="lock" size={14} />
          <span>Only you can see this. You control every share.</span>
        </div>
        <button
          type="button"
          className={styles.profile}
          onClick={() => setProfileOpen(true)}
          aria-haspopup="dialog"
          aria-label="Your account"
        >
          <span className={styles.avatar}>YV</span>
          <span className={styles.profileMeta}>
            <b>Your workspace</b>
            <span>Data controller</span>
          </span>
          <span
            className={styles.gearBtn}
            role="button"
            tabIndex={0}
            aria-label="Settings"
            onClick={(e) => {
              e.stopPropagation();
              setSettingsOpen(true);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                setSettingsOpen(true);
              }
            }}
          >
            <Icon name="settings" size={16} className={styles.gear} />
          </span>
        </button>
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
