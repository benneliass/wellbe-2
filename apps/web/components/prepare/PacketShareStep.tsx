"use client";

import { useId, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Icon } from "@wellbe/ui";
import { getApiClient } from "@/lib/api";
import { packetQueryKeys, useRevokeShareLink } from "@/lib/packet-hooks";
import { ActiveShares } from "./ActiveShares";
import { LAYER_LABELS, type VisitPacket } from "./packetFormat";
import { EXPIRY_OPTIONS, RECIPIENT_TYPES, type RecipientPurpose } from "./shareOptions";
import styles from "./PacketShare.module.css";

interface ShareResult {
  shareLinkId: string;
  token: string;
  passcodeRequired: boolean;
  expiresAt: string;
  recipient: string;
}

/** Step 3 — recipient, what they can see, expiry; then the link and every live share. */
export function PacketShareStep({ packet, onBack }: { packet: VisitPacket; onBack: () => void }) {
  const queryClient = useQueryClient();
  const revoke = useRevokeShareLink();
  const [purpose, setPurpose] = useState<RecipientPurpose>("clinician_visit");
  const [recipient, setRecipient] = useState("");
  const [hours, setHours] = useState<number>(168);
  const [passcode, setPasscode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ShareResult | null>(null);
  const [revoked, setRevoked] = useState(false);
  const [exported, setExported] = useState(false);
  const ids = { name: useId(), expiry: useId(), passcode: useId(), type: useId() };

  const included = (packet.statements ?? []).filter((s) => s.included ?? true);
  const byLayer = ["patient_prep", "summary"]
    .map((layer) => ({ layer, count: included.filter((s) => s.layer === layer).length }))
    .filter((g) => g.count > 0);

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
          params: { path: { packet_id: packet.packet_id } },
          body: {
            recipient_name: recipient.trim(),
            purpose,
            info_scope: "selected_threads",
            expires_in_hours: hours,
            passcode: passcode.trim() ? passcode.trim() : null,
          },
        },
      );
      if (apiError || !data) {
        throw new Error(
          "This packet couldn't be shared. The safety check may have flagged something — go back to Review, remove or reword it, and try again.",
        );
      }
      setRevoked(false);
      setResult({
        shareLinkId: data.share_link_id,
        token: data.share_token,
        passcodeRequired: data.passcode_required,
        expiresAt: data.expires_at,
        recipient: recipient.trim(),
      });
      void queryClient.invalidateQueries({ queryKey: packetQueryKeys.shareLinks });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong sharing this packet.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleRevoke() {
    if (!result) return;
    revoke.mutate(
      { packetId: packet.packet_id, linkId: result.shareLinkId },
      {
        onSuccess: () => setRevoked(true),
        onError: (err) => setError(err.message),
      },
    );
  }

  async function handleExport() {
    const { error: apiError } = await getApiClient().POST("/v2/visit-packets/{packet_id}/export", {
      params: { path: { packet_id: packet.packet_id } },
    });
    if (apiError) {
      setError("Couldn't export a copy. Please try again.");
      return;
    }
    setExported(true);
  }

  function resetForAnother() {
    setResult(null);
    setRecipient("");
    setPasscode("");
    setRevoked(false);
    setError(null);
  }

  const shareUrl = result
    ? typeof window !== "undefined"
      ? `${window.location.origin}/shared/${result.token}`
      : `/shared/${result.token}`
    : "";

  return (
    <div>
      {result ? (
        <section className={styles.block} aria-label="Share link created">
          <div className={styles.banner} data-tone="ok" role="status">
            <Icon name="shield-check" size={16} />
            <span>
              Link created for <b>{result.recipient}</b>. It passed the safety check and is scoped,
              time-limited, and <b>revocable</b>.
            </span>
          </div>
          <div className={styles.label}>Link (copy it now — it&rsquo;s shown only once)</div>
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
              <Icon name="lock" size={13} /> They&rsquo;ll need the passcode you set — send it
              separately.
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
              <Button
                variant="tertiary"
                icon="x-circle"
                onClick={handleRevoke}
                disabled={revoke.isPending}
              >
                Revoke access
              </Button>
            )}
            <Button variant="secondary" icon="plus" onClick={resetForAnother}>
              Share with someone else
            </Button>
          </div>
        </section>
      ) : (
        <section className={styles.block} aria-labelledby={`${ids.type}-head`}>
          <h3 id={`${ids.type}-head`} className={styles.blockHead}>
            Who is this for?
          </h3>
          <div className={styles.recipientTypes} role="radiogroup" aria-label="Recipient type">
            {RECIPIENT_TYPES.map((t) => (
              <button
                key={t.purpose}
                type="button"
                role="radio"
                aria-checked={purpose === t.purpose}
                className={styles.recipientType}
                data-on={purpose === t.purpose || undefined}
                onClick={() => setPurpose(t.purpose)}
              >
                <b>{t.label}</b>
                <span>{t.hint}</span>
              </button>
            ))}
          </div>

          <div className={styles.field}>
            <label htmlFor={ids.name}>Their name</label>
            <input
              id={ids.name}
              className={styles.input}
              placeholder="e.g. Dr. Jane Smith · City Health"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
            />
          </div>

          <div className={styles.permissions} aria-label="What they can see">
            <div className={styles.label}>What they can see</div>
            <ul className={styles.permList}>
              <li data-allowed>
                <Icon name="eye" size={14} />
                <span>
                  Only the <b>{included.length}</b> item{included.length === 1 ? "" : "s"} you
                  approved
                  {byLayer.length > 0 &&
                    ` (${byLayer.map((g) => `${g.count} ${LAYER_LABELS[g.layer]?.toLowerCase()}`).join(", ")})`}
                  , each with its source label.
                </span>
              </li>
              <li data-allowed>
                <Icon name="info" size={14} />
                <span>A note that it&rsquo;s patient-prepared and not clinician-reviewed.</span>
              </li>
              <li>
                <Icon name="x" size={14} />
                <span>
                  Nothing else in your memory — no other threads, documents, results, or items you
                  removed.
                </span>
              </li>
              <li>
                <Icon name="x" size={14} />
                <span>They can&rsquo;t edit, comment, or add to your story. View only.</span>
              </li>
            </ul>
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor={ids.expiry}>Access expires</label>
              <select
                id={ids.expiry}
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
              <label htmlFor={ids.passcode}>Passcode (optional)</label>
              <input
                id={ids.passcode}
                className={styles.input}
                placeholder="Add a passcode"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className={styles.error} role="alert">
              <Icon name="alert-circle" size={14} /> {error}
            </p>
          )}

          <div className={styles.footBtns}>
            <Button variant="tertiary" icon="arrow-left" onClick={onBack} disabled={submitting}>
              Back to review
            </Button>
            <Button variant="primary" icon="share" onClick={handleShare} disabled={submitting}>
              {submitting ? "Checking…" : "Create link"}
            </Button>
          </div>
          <p className={styles.note}>
            <Icon name="shield-check" size={13} /> A safety check runs first. You can revoke the
            link anytime.
          </p>
        </section>
      )}

      <section className={styles.block} aria-labelledby={`${ids.type}-export`}>
        <h3 id={`${ids.type}-export`} className={styles.blockHead}>
          Or export a copy
        </h3>
        <p className={styles.hint}>
          <Icon name="info" size={13} /> An exported copy can&rsquo;t be recalled once saved or
          forwarded — only link sharing can be revoked.
        </p>
        <Button variant="secondary" icon="file-text" onClick={handleExport}>
          {exported ? "Exported" : "Export copy"}
        </Button>
      </section>

      <ActiveShares />
    </div>
  );
}
