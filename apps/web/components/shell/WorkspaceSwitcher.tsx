"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { useSession } from "@/lib/useSession";
import styles from "./WorkspaceSwitcher.module.css";

type Workspace = components["schemas"]["WorkspaceV2"];

/**
 * Personal-first workspace switcher (WEL-182 / WEL-184).
 *
 * Shows the active scope and lets the user switch between the contexts they can
 * act in. It is a display-safe projection of the C17 access predicate: membership
 * is presence, never data access, so each non-personal context shows what it does
 * NOT imply. Selecting a workspace is always explicit. Sign out is here too — the
 * only way to leave a session, since there is no auto-login.
 */
export function WorkspaceSwitcher({
  onOpenProfile,
  onOpenSettings,
}: {
  onOpenProfile: () => void;
  onOpenSettings: () => void;
}) {
  const router = useRouter();
  const session = useSession();
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!session?.patientId) return;
    let active = true;
    (async () => {
      try {
        const { data } = await getApiClient().GET("/v2/workspaces");
        if (active && data) setWorkspaces(data);
      } catch {
        /* keep calm: the rail still shows the active scope from the session */
      }
    })();
    return () => {
      active = false;
    };
  }, [session?.patientId]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const active = workspaces.find((w) => w.workspace_type === "personal") ?? workspaces[0];
  const activeName = session?.displayName || active?.display_name || "Your workspace";
  const initials = toInitials(session?.displayName || "You");

  function signOut() {
    clearSession();
    setOpen(false);
    router.replace("/");
  }

  return (
    <div className={styles.wrap} ref={ref}>
      {open && (
        <div className={styles.menu} role="menu">
          <div className={styles.menuHead}>Workspaces</div>
          <ul className={styles.list}>
            {workspaces.map((w) => {
              const isActive = w.workspace_id === active?.workspace_id;
              return (
                <li key={w.workspace_id}>
                  <button type="button" className={styles.wsItem} data-active={isActive || undefined}>
                    <span className={styles.wsIcon}>
                      <Icon name={w.workspace_type === "personal" ? "user" : "users"} size={16} />
                    </span>
                    <span className={styles.wsText}>
                      <b>{w.workspace_type === "personal" ? activeName : w.display_name}</b>
                      <span>{capabilityLabel(w)}</span>
                    </span>
                    {isActive && <Icon name="check" size={16} className={styles.wsCheck} />}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className={styles.scopeNote}>
            <Icon name="shield-check" size={13} />
            Active scope: {activeName}. Membership never means access to others&rsquo; data.
          </div>
          <div className={styles.sep} />
          <button type="button" className={styles.menuItem} onClick={() => { setOpen(false); onOpenProfile(); }}>
            <Icon name="circle-user" size={16} /> Account
          </button>
          <button type="button" className={styles.menuItem} onClick={() => { setOpen(false); onOpenSettings(); }}>
            <Icon name="settings" size={16} /> Settings
          </button>
          <button type="button" className={styles.menuItem} data-danger onClick={signOut}>
            <Icon name="arrow-left" size={16} /> Sign out
          </button>
        </div>
      )}

      <button
        type="button"
        className={styles.trigger}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Workspace and account"
      >
        <span className={styles.avatar}>{initials}</span>
        <span className={styles.meta}>
          <b>{activeName}</b>
          <span>{active ? capabilityLabel(active) : "Data controller"}</span>
        </span>
        <Icon name="chevron-down" size={16} className={styles.chev} data-open={open || undefined} />
      </button>
    </div>
  );
}

function capabilityLabel(w: Workspace): string {
  const caps = (w.capability_summary ?? {}) as Record<string, boolean>;
  if (w.workspace_type === "personal") return "You control this";
  if (caps.can_contribute) return "You can contribute";
  if (caps.can_read) return "View only";
  return "No data access";
}

function toInitials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "YV";
}
