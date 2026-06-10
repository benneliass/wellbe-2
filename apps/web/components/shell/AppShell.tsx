"use client";

import { useState, type ReactNode } from "react";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { NavRail } from "./NavRail";
import styles from "./AppShell.module.css";

/** App chrome: persistent nav rail + scrollable main column, plus capture modal. */
export function AppShell({ children }: { children: ReactNode }) {
  const [captureOpen, setCaptureOpen] = useState(false);
  return (
    <div className={styles.app}>
      <NavRail onCapture={() => setCaptureOpen(true)} />
      <main className={styles.main}>{children}</main>
      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
    </div>
  );
}

/** Scrollable content region beneath a page's TopBar. */
export function PageBody({ children }: { children: ReactNode }) {
  return <div className={styles.content}>{children}</div>;
}
