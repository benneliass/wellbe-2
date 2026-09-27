"use client";

import { useState } from "react";
import { Button, Icon } from "@wellbe/ui";
import { useRevokeShareLink, useShareLinks, type ShareLinkSummary } from "@/lib/packet-hooks";
import { RECIPIENT_LABEL } from "./shareOptions";
import styles from "./PacketShare.module.css";

const STATUS_LABEL: Record<ShareLinkSummary["status"], string> = {
  active: "Active",
  expired: "Expired",
  revoked: "Revoked",
};

function when(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** Every share the person has made, with Revoke for the ones still live. */
export function ActiveShares() {
  const links = useShareLinks();
  const revoke = useRevokeShareLink();
  const [error, setError] = useState<string | null>(null);

  const rows = links.data ?? [];
  const active = rows.filter((l) => l.status === "active");
  const past = rows.filter((l) => l.status !== "active");

  function handleRevoke(link: ShareLinkSummary) {
    setError(null);
    revoke.mutate(
      { packetId: link.packet_id, linkId: link.share_link_id },
      { onError: (err) => setError(err.message) },
    );
  }

  function row(link: ShareLinkSummary) {
    const live = link.status === "active";
    return (
      <li key={link.share_link_id} className={styles.shareRow} data-status={link.status}>
        <div className={styles.shareMain}>
          <b>{link.recipient_name}</b>
          <span className={styles.shareMeta}>
            {RECIPIENT_LABEL[link.purpose] ?? "Shared"} · {link.packet_title}
            {link.passcode_required ? " · passcode" : ""}
          </span>
          <span className={styles.shareMeta}>
            {live
              ? `Expires ${when(link.expires_at)}`
              : link.status === "revoked" && link.revoked_at
                ? `Revoked ${when(link.revoked_at)}`
                : `Expired ${when(link.expires_at)}`}
          </span>
        </div>
        <span className={styles.statusPill} data-status={link.status}>
          {STATUS_LABEL[link.status]}
        </span>
        {live && (
          <Button
            variant="tertiary"
            icon="x-circle"
            aria-label={`Revoke access for ${link.recipient_name}`}
            onClick={() => handleRevoke(link)}
            disabled={revoke.isPending}
          >
            Revoke
          </Button>
        )}
      </li>
    );
  }

  return (
    <section className={styles.block} aria-labelledby="active-shares-head">
      <h3 id="active-shares-head" className={styles.blockHead}>
        Your shares
      </h3>
      {links.isLoading ? (
        <p className={styles.hint}>Loading your shares…</p>
      ) : links.isError ? (
        <p className={styles.hint}>
          <Icon name="info" size={13} /> Your shares couldn&rsquo;t be loaded right now.
        </p>
      ) : rows.length === 0 ? (
        <p className={styles.hint}>You haven&rsquo;t shared a packet yet.</p>
      ) : (
        <>
          {active.length === 0 ? (
            <p className={styles.hint}>No links are active right now.</p>
          ) : (
            <ul className={styles.shareList} aria-label="Active shares">
              {active.map(row)}
            </ul>
          )}
          {past.length > 0 && (
            <details className={styles.past}>
              <summary>Ended shares ({past.length})</summary>
              <ul className={styles.shareList} aria-label="Ended shares">
                {past.map(row)}
              </ul>
            </details>
          )}
        </>
      )}
      {error && (
        <p className={styles.error} role="alert">
          <Icon name="alert-circle" size={14} /> {error}
        </p>
      )}
      <p className={styles.hint}>
        <Icon name="info" size={13} /> Revoking stops future access through the link. A copy someone
        already saved or exported can&rsquo;t be recalled.
      </p>
    </section>
  );
}
