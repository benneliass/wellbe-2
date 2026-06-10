"use client";

import { useState } from "react";
import { Button } from "@wellbe/ui";
import type { Thread } from "@/lib/types";
import { ShareSheet } from "./ShareSheet";
import styles from "./ThreadDetail.module.css";

/** The "What next?" actions. Owns the share-sheet modal state. */
export function NextActions({ thread }: { thread: Thread }) {
  const [shareOpen, setShareOpen] = useState(false);
  return (
    <>
      <div className={styles.next}>
        <Button variant="primary" icon="share" full onClick={() => setShareOpen(true)}>
          Share this thread
        </Button>
        <Button variant="secondary" icon="message-circle" full>
          Add a question to ask
        </Button>
        <Button variant="tertiary" icon="shield-check" full>
          Correct something
        </Button>
      </div>
      {shareOpen && <ShareSheet thread={thread} onClose={() => setShareOpen(false)} />}
    </>
  );
}
