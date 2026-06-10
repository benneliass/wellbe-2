"use client";

import type { ReactNode } from "react";
import { Icon } from "../Icon";
import styles from "./Modal.module.css";

export interface ModalProps {
  title: string;
  icon: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

/** Centered dialog with scrim. Click-outside and the close button both dismiss. */
export function Modal({ title, icon, onClose, children, footer, wide }: ModalProps) {
  return (
    <div className={styles.scrim} onClick={onClose} role="presentation">
      <div
        className={styles.modal}
        data-wide={wide || undefined}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <div className={styles.title}>
            <Icon name={icon} size={18} />
            {title}
          </div>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.foot}>{footer}</div>}
      </div>
    </div>
  );
}
