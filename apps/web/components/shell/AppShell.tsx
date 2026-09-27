"use client";

import { useState, type ReactNode } from "react";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { BottomNav } from "./BottomNav";
import { NavRail } from "./NavRail";
import styles from "./AppShell.module.css";

/**
 * App chrome: desktop nav rail (mobile: slim header) + scrollable main column,
 * the mobile bottom nav, and the capture modal both navs open.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const [captureOpen, setCaptureOpen] = useState(false);
  const openCapture = () => setCaptureOpen(true);
  return (
    <div className={styles.app}>
      <NavRail onCapture={openCapture} />
      <main id="main" className={styles.main}>
        {children}
      </main>
      <BottomNav onCapture={openCapture} />
      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
    </div>
  );
}

/** Scrollable content region beneath a page's TopBar. */
export function PageBody({ children }: { children: ReactNode }) {
  return <div className={styles.content}>{children}</div>;
}
