"use client";

import { useRef, useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import { CAPTURE_TYPES } from "@/lib/meta";
import styles from "./CaptureModal.module.css";

const SEVERITIES = ["Mild", "Moderate", "Severe"];

export function CaptureModal({ onClose }: { onClose: () => void }) {
  const [type, setType] = useState("reported");
  const [severity, setSeverity] = useState("Mild");
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const footer = (
    <>
      <span className={styles.note}>
        <Icon name="lock" size={13} />
        Saved privately to your memory
      </span>
      <div className={styles.footBtns}>
        <Button variant="tertiary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" icon="check" onClick={onClose}>
          Add to memory
        </Button>
      </div>
    </>
  );

  return (
    <Modal title="Capture" icon="plus-circle" onClose={onClose} footer={footer}>
      <div className={styles.label}>What are you capturing?</div>
      <div className={styles.types}>
        {CAPTURE_TYPES.map((t) => (
          <button
            key={t.id}
            type="button"
            className={styles.type}
            data-active={type === t.id || undefined}
            onClick={() => setType(t.id)}
          >
            <span className={styles.typeIcon}>
              <Icon name={t.icon} size={18} />
            </span>
            <span className={styles.typeText}>
              <b>{t.label}</b>
              <span>{t.hint}</span>
            </span>
            {type === t.id && <Icon name="check-circle-2" size={16} className={styles.check} />}
          </button>
        ))}
      </div>

      {/* Type-specific fields — each capture type asks for what it needs. */}
      {type === "reported" && (
        <>
          <div className={styles.field}>
            <label htmlFor="capture-desc">What are you feeling?</label>
            <textarea
              id="capture-desc"
              placeholder="Describe the symptom in your own words…"
              rows={3}
            />
          </div>
          <div className={styles.field}>
            <label>How intense is it?</label>
            <div className={styles.choices}>
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={styles.choice}
                  data-active={severity === s || undefined}
                  onClick={() => setSeverity(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {type === "lab" && (
        <>
          <div className={styles.field}>
            <label htmlFor="lab-name">Test name</label>
            <input id="lab-name" type="text" placeholder="e.g. Vitamin D, HbA1c, LDL…" />
          </div>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="lab-value">Value</label>
              <input id="lab-value" type="text" inputMode="decimal" placeholder="e.g. 32" />
            </div>
            <div className={styles.field}>
              <label htmlFor="lab-unit">Unit</label>
              <input id="lab-unit" type="text" placeholder="e.g. ng/mL" />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="lab-range">Reference range (optional)</label>
            <input id="lab-range" type="text" placeholder="e.g. 30–100 ng/mL" />
          </div>
        </>
      )}

      {type === "doc" && (
        <div className={styles.field}>
          <label>Document</label>
          <button
            type="button"
            className={styles.dropzone}
            data-has-file={fileName ? true : undefined}
            onClick={() => fileInputRef.current?.click()}
          >
            <span className={styles.dropIcon}>
              <Icon name={fileName ? "file-text" : "upload-cloud"} size={22} />
            </span>
            {fileName ? (
              <span className={styles.dropFile}>{fileName}</span>
            ) : (
              <>
                <span className={styles.dropText}>
                  <b>Click to browse</b> or drag a file here
                </span>
                <span className={styles.dropHint}>PDF, photo, or report — up to 25 MB</span>
              </>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,image/*"
            hidden
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
        </div>
      )}

      {type === "note" && (
        <div className={styles.field}>
          <label htmlFor="note-body">Your note</label>
          <textarea
            id="note-body"
            placeholder="A thought, a question for your doctor, anything to remember…"
            rows={4}
          />
        </div>
      )}

      {/* Common metadata for every capture type. */}
      <div className={styles.fieldRow}>
        <div className={styles.field}>
          <label>When</label>
          <div className={styles.input}>
            <Icon name="calendar" size={15} />
            <span>Today, 9:24 AM</span>
          </div>
        </div>
        <div className={styles.field}>
          <label>Attach to thread</label>
          <div className={styles.input}>
            <Icon name="list" size={15} />
            <span>Lower back pain</span>
            <Icon name="chevron-down" size={15} className={styles.chev} />
          </div>
        </div>
      </div>
    </Modal>
  );
}
