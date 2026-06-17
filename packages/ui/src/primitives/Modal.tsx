"use client";

import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
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

/**
 * Centered dialog with scrim. Click-outside and the close button both dismiss.
 *
 * Rendered through a portal to document.body so the fixed-position scrim is
 * never captured by an ancestor's positioning, overflow, or transform context
 * (e.g. a `position: relative; overflow: hidden` page shell would otherwise
 * trap the dialog in normal flow and clip it out of view).
 */
export function Modal({ title, icon, onClose, children, footer, wide }: ModalProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return createPortal(
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
    </div>,
    document.body,
  );
}
