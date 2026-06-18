"use client";

import { useState } from "react";
import { Button } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import type { Thread } from "@/lib/types";
import { ShareSheet } from "./ShareSheet";
import styles from "./ThreadDetail.module.css";

/** The "What next?" actions. Owns the share-sheet and capture modal state. */
export function NextActions({ thread }: { thread: Thread }) {
  const [shareOpen, setShareOpen] = useState(false);
  // Both "add a question" and "correct something" are captured as durable notes
  // (the real write path, WEL-155) rather than fake no-op buttons.
  const [capture, setCapture] = useState<null | "note">(null);
  return (
    <>
      <div className={styles.next}>
        <Button variant="primary" icon="share" full onClick={() => setShareOpen(true)}>
          Share this thread
        </Button>
        <Button variant="secondary" icon="message-circle" full onClick={() => setCapture("note")}>
          Add a question to ask
        </Button>
        <Button variant="tertiary" icon="shield-check" full onClick={() => setCapture("note")}>
          Correct something
        </Button>
      </div>
      {shareOpen && <ShareSheet thread={thread} onClose={() => setShareOpen(false)} />}
      {capture && (
        <CaptureModal initialType="note" onClose={() => setCapture(null)} />
      )}
    </>
  );
}
