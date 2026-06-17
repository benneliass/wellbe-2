"use client";

import { Button, Icon, Modal } from "@wellbe/ui";
import styles from "./AccountModals.module.css";

interface ProfileModalProps {
  onClose: () => void;
  /** Cross-link to the Settings dialog so the gear and avatar share one surface. */
  onOpenSettings: () => void;
}

/**
 * PROFILE / account — prototype surface.
 *
 * Identity is static mock data today. The rows reflect WellBe's stance: the
 * individual is the data controller, and sharing is always grant-scoped and
 * revocable. Actions are local-only until the account API lands.
 */
export function ProfileModal({ onClose, onOpenSettings }: ProfileModalProps) {
  const footer = (
    <>
      <Button variant="tertiary" icon="settings" onClick={onOpenSettings}>
        Settings
      </Button>
      <Button variant="primary" icon="check" onClick={onClose}>
        Done
      </Button>
    </>
  );

  return (
    <Modal title="Your account" icon="circle-user" onClose={onClose} footer={footer}>
      <div className={styles.identity}>
        <span className={styles.identityAvatar}>A</span>
        <span className={styles.identityMeta}>
          <span className={styles.identityName}>Your workspace</span>
          <span className={styles.identityRole}>
            <Icon name="shield-check" size={13} />
            Data controller
          </span>
        </span>
      </div>

      <div className={styles.note}>
        <Icon name="lock" size={15} />
        <span>
          This is your personal workspace. Your data belongs to you — only you can see it, and every
          share is your decision.
        </span>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Account</div>
        <button type="button" className={`${styles.row} ${styles.linkRow}`} onClick={onOpenSettings}>
          <span className={styles.rowIcon}>
            <Icon name="user" size={18} />
          </span>
          <span className={styles.rowText}>
            <span className={styles.rowMain}>Profile &amp; identity</span>
            <span className={styles.rowSub}>Your name, contact, and workspace details.</span>
          </span>
          <Icon name="chevron-right" size={18} className={styles.rowChev} />
        </button>
        <button type="button" className={`${styles.row} ${styles.linkRow}`} onClick={onOpenSettings}>
          <span className={styles.rowIcon}>
            <Icon name="share" size={18} />
          </span>
          <span className={styles.rowText}>
            <span className={styles.rowMain}>Sharing &amp; grants</span>
            <span className={styles.rowSub}>Review who you&rsquo;ve granted access to, and revoke anytime.</span>
          </span>
          <Icon name="chevron-right" size={18} className={styles.rowChev} />
        </button>
        <button type="button" className={`${styles.row} ${styles.linkRow}`} onClick={onOpenSettings}>
          <span className={styles.rowIcon}>
            <Icon name="shield-check" size={18} />
          </span>
          <span className={styles.rowText}>
            <span className={styles.rowMain}>Privacy controls</span>
            <span className={styles.rowSub}>Manage approvals, comparison opt-in, and notifications.</span>
          </span>
          <Icon name="chevron-right" size={18} className={styles.rowChev} />
        </button>
      </div>
    </Modal>
  );
}
