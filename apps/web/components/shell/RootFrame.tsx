"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { PRIMARY_NAV, isNavActive } from "@/lib/meta";
import { useSession } from "@/lib/useSession";
import { BottomNav } from "./BottomNav";
import styles from "./RootFrame.module.css";

const RootNavContext = createContext<ReactNode>(null);

/**
 * The launcher's desktop primary nav, for the launcher header to place beside
 * its wordmark. `null` when the root path shows no app navigation.
 */
export function useRootNav(): ReactNode {
  return useContext(RootNavContext);
}

/**
 * Landmarks for the root path, which renders outside the workspace AppShell.
 * The front door (no session) gets only a <main>; once a session is onboarded
 * the launcher also gets the primary nav — bottom bar on mobile, a compact menu
 * in the header on desktop.
 */
export function RootFrame({ children }: { children: ReactNode }) {
  const session = useSession();
  const [captureOpen, setCaptureOpen] = useState(false);
  const withNav = Boolean(session?.onboarded);
  const openCapture = () => setCaptureOpen(true);

  return (
    <RootNavContext.Provider value={withNav ? <LauncherNav onCapture={openCapture} /> : null}>
      <main id="main" className={withNav ? styles.withNav : undefined}>
        {children}
      </main>
      {withNav && <BottomNav variant="shell" onCapture={openCapture} />}
      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
    </RootNavContext.Provider>
  );
}

/**
 * Desktop (>= 768px) primary nav: the destinations sit behind a "Menu" button
 * so they take no width from the pill row.
 */
function LauncherNav({ onCapture }: { onCapture: () => void }) {
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    const onPointer = (e: PointerEvent) => {
      if (!navRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <nav ref={navRef} aria-label="Primary" className={styles.nav} data-open={open || undefined}>
      <button
        ref={buttonRef}
        type="button"
        className={styles.menuBtn}
        aria-expanded={open}
        aria-controls="root-nav-list"
        onClick={() => setOpen((o) => !o)}
      >
        Menu
        <Icon name={open ? "x" : "chevron-down"} size={16} />
      </button>
      <ul id="root-nav-list" className={styles.list}>
        {PRIMARY_NAV.map((item) => {
          const content = (
            <>
              <span className={styles.icon}>
                <Icon name={item.icon} size={20} />
              </span>
              <span className={styles.label}>{item.label}</span>
            </>
          );
          if (item.action === "capture") {
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className={styles.item}
                  data-capture="true"
                  aria-haspopup="dialog"
                  onClick={() => {
                    setOpen(false);
                    onCapture();
                  }}
                >
                  {content}
                </button>
              </li>
            );
          }
          const active = isNavActive(item, pathname);
          return (
            <li key={item.id}>
              <Link
                href={item.href}
                className={styles.item}
                aria-current={active ? "page" : undefined}
                onClick={() => setOpen(false)}
              >
                {content}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
