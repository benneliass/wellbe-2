"use client";

import { useRouter } from "next/navigation";
import { Button, Icon, Modal } from "@wellbe/ui";
import { useAccount } from "@/lib/account";
import { signOut } from "@/lib/auth";
import styles from "./AccountModals.module.css";

interface ProfileModalProps {
  onClose: () => void;
  /** Cross-link to the Settings dialog so the gear and avatar share one surface. */
  onOpenSettings: () => void;
}

/**
 * PROFILE / account. Shows who is signed in (from the session). The rows reflect
 * WellBe's stance: the individual is the data controller, and sharing is always
 * grant-scoped and revocable.
 */
export function ProfileModal({ onClose, onOpenSettings }: ProfileModalProps) {
  const router = useRouter();
  const account = useAccount();

  async function onSignOut() {
    onClose();
    await signOut();
    router.replace("/");
  }

  const footer = (
    <>
      <Button variant="tertiary" icon="arrow-left" onClick={onSignOut}>
        Sign out
      </Button>
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
        <span className={styles.identityAvatar}>{account.initials}</span>
        <span className={styles.identityMeta}>
          <span className={styles.identityName}>{account.name}</span>
          {account.email && account.email !== account.name && (
            <span className={styles.identityEmail}>{account.email}</span>
          )}
          <span className={styles.identityEmail}>{account.signInMethod}</span>
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
