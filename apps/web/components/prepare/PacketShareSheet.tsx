"use client";

import { useState } from "react";
import { Button, Icon, Modal } from "@wellbe/ui";
import { getApiClient } from "@/lib/api";
import styles from "./PacketShareSheet.module.css";

const EXPIRY_OPTIONS = [
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 168 },
  { label: "30 days", hours: 720 },
];

interface ShareResult {
  shareLinkId: string;
  token: string;
  passcodeRequired: boolean;
  expiresAt: string;
}

export function PacketShareSheet({
  packetId,
  packetTitle,
  onClose,
}: {
  packetId: string;
  packetTitle: string;
  onClose: () => void;
}) {
  const [recipient, setRecipient] = useState("");
  const [hours, setHours] = useState(168);
  const [passcode, setPasscode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ShareResult | null>(null);
  const [revoked, setRevoked] = useState(false);

  async function handleShare() {
    if (!recipient.trim()) {
      setError("Add who you're sharing this with.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const { data, error: apiError } = await getApiClient().POST(
        "/v2/visit-packets/{packet_id}/share",
        {
          params: { path: { packet_id: packetId } },
          body: {
            recipient_name: recipient.trim(),
            purpose: "clinician_visit",
            info_scope: "selected_threads",
            expires_in_hours: hours,
            passcode: passcode.trim() ? passcode.trim() : null,
          },
        },
      );
      if (apiError || !data) {
        throw new Error(
          "This packet couldn't be shared. The safety check may have flagged something — review and try again.",
        );
      }
      setResult({
        shareLinkId: data.share_link_id,
        token: data.share_token,
        passcodeRequired: data.passcode_required,
        expiresAt: data.expires_at,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong sharing this packet.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke() {
    if (!result) return;
    setSubmitting(true);
    try {
      await getApiClient().POST("/v2/visit-packets/{packet_id}/share/{link_id}/revoke", {
        params: { path: { packet_id: packetId, link_id: result.shareLinkId } },
      });
      setRevoked(true);
    } finally {
      setSubmitting(false);
    }
  }

  const shareUrl =
    result && typeof window !== "undefined"
      ? `${window.location.origin}/shared/${result.token}`
      : result
        ? `/shared/${result.token}`
        : "";

  if (result) {
    return (
      <Modal title="Share link created" icon="share" onClose={onClose} wide>
        <div className={styles.banner} data-tone="ok">
          <Icon name="shield-check" size={16} />
          <span>
            Passed the safety check. This link is scoped, time-limited, and{" "}
            <b>revocable</b> — but an exported or saved copy can&rsquo;t be recalled.
          </span>
        </div>

        <div className={styles.label}>One-time link (copy it now)</div>
        <div className={styles.tokenBox}>
          <code>{shareUrl}</code>
          <Button
            variant="tertiary"
            icon="clipboard-list"
            onClick={() => navigator.clipboard?.writeText(shareUrl)}
          >
            Copy
          </Button>
        </div>

        {result.passcodeRequired && (
          <p className={styles.hint}>
            <Icon name="lock" size={13} /> The recipient must enter the passcode you set.
          </p>
        )}
        <p className={styles.hint}>
          <Icon name="clock" size={13} /> Expires {new Date(result.expiresAt).toLocaleString()}
        </p>

        <div className={styles.footBtns}>
          {revoked ? (
            <span className={styles.revoked}>
              <Icon name="check" size={14} /> Access revoked
            </span>
          ) : (
            <Button variant="tertiary" icon="x-circle" onClick={handleRevoke} disabled={submitting}>
              Revoke access
            </Button>
          )}
          <Button variant="primary" onClick={onClose}>
            Done
          </Button>
        </div>
      </Modal>
    );
  }

  const footer = (
    <>
      <span className={styles.note}>
        <Icon name="shield-check" size={13} />
        You can revoke this access anytime
      </span>
      <div className={styles.footBtns}>
        <Button variant="tertiary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" icon="share" onClick={handleShare} disabled={submitting}>
          {submitting ? "Checking…" : "Create link"}
        </Button>
      </div>
    </>
  );

  return (
    <Modal title="Share packet" icon="share" onClose={onClose} wide footer={footer}>
      <div className={styles.banner}>
        <Icon name="lock" size={16} />
        <span>
          You are the data controller. Sharing &ldquo;{packetTitle}&rdquo; creates a{" "}
          <b>scoped, revocable grant</b> after a safety check — the recipient sees only what you
          included.
        </span>
      </div>

      <div className={styles.label}>Share with</div>
      <input
        className={styles.input}
        placeholder="e.g. Dr. Jane Smith · City Health"
        value={recipient}
        onChange={(e) => setRecipient(e.target.value)}
      />

      <div className={styles.fieldRow}>
        <div className={styles.field}>
          <label>Access expires</label>
          <select
            className={styles.select}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          >
            {EXPIRY_OPTIONS.map((o) => (
              <option key={o.hours} value={o.hours}>
                In {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label>Passcode (optional)</label>
          <input
            className={styles.input}
            placeholder="Add a passcode"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <p className={styles.error}>
          <Icon name="alert-circle" size={14} /> {error}
        </p>
      )}
    </Modal>
  );
}
