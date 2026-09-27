"use client";

import { useId, useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import { useCaptureToThread } from "@/lib/thread-hooks";
import styles from "./ThreadDetailLive.module.css";

const NOTE_MAX = 4000;

/**
 * Capture pre-attached to one thread: the user's own words, stored verbatim as a
 * note with this thread as its home. Opened from the Clarify strip and the Voice lane.
 */
export function ThreadCaptureSheet({
  threadId,
  threadTitle,
  prompt,
  onClose,
}: {
  threadId: string;
  threadTitle: string;
  /** The question being answered, shown above the text box. */
  prompt?: string;
  onClose: () => void;
}) {
  const id = useId();
  const capture = useCaptureToThread(threadId);
  const [text, setText] = useState("");
  const [idempotencyKey] = useState(() => `web-thread-note-${crypto.randomUUID()}`);

  if (capture.isSuccess) {
    return (
      <Modal
        title="Added to your story"
        icon="check-circle-2"
        onClose={onClose}
        footer={
          <Button icon="check" onClick={onClose}>
            Done
          </Button>
        }
      >
        <p className={styles.sheetText} role="status">
          Saved privately in your words, attached to {threadTitle}. WellBe is sorting it in now — it
          will show up here shortly.
        </p>
      </Modal>
    );
  }

  const ready = text.trim().length > 0 && !capture.isPending;

  return (
    <Modal
      title={`Add to ${threadTitle}`}
      icon="message-circle"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={capture.isPending}>
            Cancel
          </Button>
          <Button
            icon="check"
            disabled={!ready}
            onClick={() => capture.mutate({ text: text.trim(), idempotencyKey })}
          >
            {capture.isPending ? "Saving…" : "Save in my words"}
          </Button>
        </>
      }
    >
      <div className={styles.sheet}>
        {prompt && (
          <p className={styles.sheetPrompt} id={`${id}-prompt`}>
            <Icon name="circle-help" size={15} />
            {prompt}
          </p>
        )}
        <label className={styles.sheetLabel} htmlFor={`${id}-text`}>
          In your own words
        </label>
        <textarea
          id={`${id}-text`}
          className={styles.sheetInput}
          rows={5}
          maxLength={NOTE_MAX}
          value={text}
          aria-describedby={prompt ? `${id}-prompt` : undefined}
          onChange={(e) => setText(e.target.value)}
        />
        <p className={styles.sheetNote}>Kept exactly as you write it. Nothing here is a diagnosis.</p>
        {capture.isError && (
          <p className={styles.sheetError} role="alert">
            {capture.error.message}
          </p>
        )}
      </div>
    </Modal>
  );
}
