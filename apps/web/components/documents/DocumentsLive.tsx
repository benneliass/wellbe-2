"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Icon } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { StateNote } from "@/components/placeholder/StateNote";
import { formatDate } from "@/lib/records-format";
import { recordsKeys, useDocuments, type DocumentRecord } from "@/lib/records-hooks";
import styles from "./DocumentsLive.module.css";

const STATUS_ICON: Record<DocumentRecord["status"], string> = {
  processed: "check-circle-2",
  waiting: "clock",
  could_not_read: "file-search",
};

export function DocumentsLive() {
  const { data, isPending, isError, refetch, signedIn } = useDocuments();
  const queryClient = useQueryClient();
  const [captureOpen, setCaptureOpen] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  if (signedIn === false) {
    return (
      <div className={styles.wrap}>
        <StateNote
          icon="file-text"
          title="Sign in to see your documents"
          description="Documents you add are stored privately and unchanged. Sign in to see them."
        />
      </div>
    );
  }

  if (signedIn === undefined || isPending) {
    return (
      <div className={styles.wrap}>
        <p className={styles.hint} role="status">
          <Icon name="file-text" size={16} />
          Gathering your documents…
        </p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className={styles.wrap}>
        <div className={styles.problem} role="alert">
          <p>We couldn&apos;t load your documents just now. Nothing is lost — please try again.</p>
          <Button variant="secondary" icon="rotate-ccw" onClick={() => void refetch()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <section className={styles.intro} aria-labelledby="documents-headline">
        <h2 id="documents-headline" className={styles.headline}>
          {data.headline}
        </h2>
        <p className={styles.note}>{data.note}</p>
        <div className={styles.actions}>
          <Button variant="primary" icon="upload-cloud" onClick={() => setCaptureOpen(true)}>
            Add a document
          </Button>
        </div>
        {justSaved && (
          <p className={styles.saved} role="status">
            <Icon name="check-circle-2" size={16} />
            Saved. WellBe will read it in the next few minutes.
          </p>
        )}
      </section>

      {data.documents.length === 0 ? (
        <StateNote
          icon="upload-cloud"
          title="Add your first document"
          description="Add a lab report, letter, or discharge summary. WellBe keeps the original and shows what it found."
        />
      ) : (
        <ul className={styles.list} aria-label="Your documents">
          {data.documents.map((d) => (
            <DocumentCard key={d.document_id} doc={d} />
          ))}
        </ul>
      )}

      {captureOpen && (
        <CaptureModal
          initialType="doc"
          onClose={() => setCaptureOpen(false)}
          onCaptured={() => {
            setJustSaved(true);
            void queryClient.invalidateQueries({ queryKey: recordsKeys.documents });
          }}
        />
      )}
    </div>
  );
}

function extractedSummary(doc: DocumentRecord): string {
  return doc.extracted.map((e) => `${e.count} ${e.label}`).join(", ");
}

function DocumentCard({ doc }: { doc: DocumentRecord }) {
  const headingId = `document-${doc.document_id}-title`;
  return (
    <li
      id={`document-${doc.document_id}`}
      className={styles.card}
      aria-labelledby={headingId}
      tabIndex={-1}
    >
      <div className={styles.cardHead}>
        <span className={styles.typeIcon} aria-hidden="true">
          <Icon name="file-text" size={20} />
        </span>
        <div className={styles.titles}>
          <h3 id={headingId} className={styles.name}>
            {doc.display_label}
          </h3>
          <p className={styles.meta}>
            <span>{doc.type_label}</span>
            <span aria-hidden="true"> · </span>
            <span>Added {formatDate(doc.added_at)}</span>
          </p>
        </div>
      </div>

      <p className={styles.status} data-status={doc.status}>
        <Icon name={STATUS_ICON[doc.status]} size={16} />
        <span>
          <b>{doc.status_label}.</b> {doc.status_detail}
        </span>
      </p>

      {doc.extracted_total > 0 && (
        <p className={styles.found}>
          <span className={styles.foundLabel}>What WellBe found:</span> {extractedSummary(doc)}
        </p>
      )}

      {doc.result_count > 0 && (
        <Link href={`/results?document=${encodeURIComponent(doc.document_id)}`} className={styles.link}>
          <Icon name="flask-conical" size={15} />
          <span>
            See {doc.result_count} result{doc.result_count === 1 ? "" : "s"} from this document
          </span>
          <Icon name="arrow-right" size={15} />
        </Link>
      )}
    </li>
  );
}
