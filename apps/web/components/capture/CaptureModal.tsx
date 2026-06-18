"use client";

import { useRef, useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { CAPTURE_TYPES } from "@/lib/meta";
import styles from "./CaptureModal.module.css";

const SEVERITIES = ["Mild", "Moderate", "Severe"];

type CaptureType = components["schemas"]["CaptureType"];

/**
 * UI capture-type id (from CAPTURE_TYPES) -> backend capture_type. The UI ids are
 * product labels; the write path (WEL-155) speaks symptom/lab/document/note.
 */
const TYPE_MAP: Record<string, CaptureType> = {
  reported: "symptom",
  lab: "lab",
  doc: "document",
  note: "note",
};

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("Could not read file"));
    reader.onload = () => {
      const result = reader.result as string;
      // Strip the "data:<mime>;base64," prefix — the API wants raw base64.
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(file);
  });
}

export function CaptureModal({
  onClose,
  onCaptured,
  initialType = "reported",
}: {
  onClose: () => void;
  /** Called after a capture is durably stored, so callers can refresh. */
  onCaptured?: (captureId: string) => void;
  /** Pre-select a capture type (e.g. "note" when adding a question). */
  initialType?: string;
}) {
  const [type, setType] = useState(initialType);
  const [severity, setSeverity] = useState("Mild");
  const [description, setDescription] = useState("");
  const [note, setNote] = useState("");
  const [labName, setLabName] = useState("");
  const [labValue, setLabValue] = useState("");
  const [labUnit, setLabUnit] = useState("");
  const [labRange, setLabRange] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Stable across error-retries of the same capture so a retried submit is
  // idempotent (one permanent raw record); reset only after a clean success.
  const idempotencyKeyRef = useRef<string | null>(null);

  async function buildPayload(): Promise<Record<string, unknown>> {
    switch (type) {
      case "reported":
        return { description: description.trim(), severity };
      case "note":
        return { text: note.trim() };
      case "lab":
        return {
          test_name: labName.trim(),
          value: labValue.trim(),
          unit: labUnit.trim() || undefined,
          reference_range: labRange.trim() || undefined,
        };
      case "doc": {
        if (!file) throw new Error("Choose a document to upload first.");
        return {
          content_base64: await readFileAsBase64(file),
          mime_type: file.type || "application/pdf",
          filename: file.name,
        };
      }
      default:
        return {};
    }
  }

  function clientValidationError(): string | null {
    if (type === "reported" && !description.trim()) return "Describe what you're feeling first.";
    if (type === "note" && !note.trim()) return "Write your note first.";
    if (type === "lab" && (!labName.trim() || !labValue.trim()))
      return "Add the test name and value first.";
    if (type === "doc" && !file) return "Choose a document to upload first.";
    return null;
  }

  async function handleSubmit() {
    const validation = clientValidationError();
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    setSubmitting(true);
    if (!idempotencyKeyRef.current) idempotencyKeyRef.current = crypto.randomUUID();
    try {
      const captureType = TYPE_MAP[type];
      if (!captureType) throw new Error("Unknown capture type.");
      const payload = await buildPayload();
      const { data, error: apiError } = await getApiClient().POST("/v1/capture", {
        params: { header: { "Idempotency-Key": idempotencyKeyRef.current } },
        body: {
          schema_version: "c13.capture.request.v1",
          capture_type: captureType,
          payload,
        },
      });
      if (apiError || !data) {
        throw new Error("The capture could not be saved. Please try again.");
      }
      idempotencyKeyRef.current = null;
      onCaptured?.(data.capture_id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong saving your capture.");
    } finally {
      setSubmitting(false);
    }
  }

  const footer = (
    <>
      {error ? (
        <span className={styles.error}>
          <Icon name="alert-circle" size={13} />
          {error}
        </span>
      ) : (
        <span className={styles.note}>
          <Icon name="lock" size={13} />
          Saved privately to your memory
        </span>
      )}
      <div className={styles.footBtns}>
        <Button variant="tertiary" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button variant="primary" icon="check" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Saving…" : "Add to memory"}
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
            onClick={() => {
              setType(t.id);
              setError(null);
            }}
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
              value={description}
              onChange={(e) => setDescription(e.target.value)}
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
            <input
              id="lab-name"
              type="text"
              placeholder="e.g. Vitamin D, HbA1c, LDL…"
              value={labName}
              onChange={(e) => setLabName(e.target.value)}
            />
          </div>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="lab-value">Value</label>
              <input
                id="lab-value"
                type="text"
                inputMode="decimal"
                placeholder="e.g. 32"
                value={labValue}
                onChange={(e) => setLabValue(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="lab-unit">Unit</label>
              <input
                id="lab-unit"
                type="text"
                placeholder="e.g. ng/mL"
                value={labUnit}
                onChange={(e) => setLabUnit(e.target.value)}
              />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="lab-range">Reference range (optional)</label>
            <input
              id="lab-range"
              type="text"
              placeholder="e.g. 30–100 ng/mL"
              value={labRange}
              onChange={(e) => setLabRange(e.target.value)}
            />
          </div>
        </>
      )}

      {type === "doc" && (
        <div className={styles.field}>
          <label>Document</label>
          <button
            type="button"
            className={styles.dropzone}
            data-has-file={file ? true : undefined}
            onClick={() => fileInputRef.current?.click()}
          >
            <span className={styles.dropIcon}>
              <Icon name={file ? "file-text" : "upload-cloud"} size={22} />
            </span>
            {file ? (
              <span className={styles.dropFile}>{file.name}</span>
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
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setError(null);
            }}
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
            value={note}
            onChange={(e) => setNote(e.target.value)}
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
