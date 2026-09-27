"use client";

import { useState, type ReactNode } from "react";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { useSession } from "@/lib/useSession";
import { BottomNav } from "./BottomNav";
import styles from "./RootFrame.module.css";

/**
 * Landmarks for the root path, which renders outside the workspace AppShell.
 * The front door (no session) gets only a <main>; once a session is onboarded
 * the launcher also gets the primary nav — bottom bar on mobile, left dock on desktop.
 */
export function RootFrame({ children }: { children: ReactNode }) {
  const session = useSession();
  const [captureOpen, setCaptureOpen] = useState(false);
  const withNav = Boolean(session?.onboarded);

  return (
    <>
      <main id="main" className={withNav ? styles.withNav : undefined}>
        {children}
      </main>
      {withNav && <BottomNav variant="dock" onCapture={() => setCaptureOpen(true)} />}
      {captureOpen && <CaptureModal onClose={() => setCaptureOpen(false)} />}
    </>
  );
}
