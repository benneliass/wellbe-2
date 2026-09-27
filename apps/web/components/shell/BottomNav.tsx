"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@wellbe/ui";
import { PRIMARY_NAV, isNavActive } from "@/lib/meta";
import styles from "./BottomNav.module.css";

export interface BottomNavProps {
  onCapture: () => void;
  /**
   * `shell`: mobile-only bar; the desktop rail carries navigation at >= 768px.
   * `dock`: also shown on desktop as a floating dock, for surfaces without a rail.
   */
  variant?: "shell" | "dock";
}

/** Primary navigation for the five destinations: fixed bottom bar on mobile. */
export function BottomNav({ onCapture, variant = "shell" }: BottomNavProps) {
  const pathname = usePathname() ?? "/";

  return (
    <nav aria-label="Primary" className={styles.bar} data-variant={variant}>
      <ul className={styles.list}>
        {PRIMARY_NAV.map((item) => {
          if (item.action === "capture") {
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className={styles.item}
                  data-capture="true"
                  aria-haspopup="dialog"
                  onClick={onCapture}
                >
                  <span className={styles.icon}>
                    <Icon name={item.icon} size={22} />
                  </span>
                  <span className={styles.label}>{item.label}</span>
                </button>
              </li>
            );
          }
          const active = isNavActive(item, pathname);
          return (
            <li key={item.id}>
              <Link
                href={item.href}
                className={styles.item}
                aria-current={active ? "page" : undefined}
              >
                <span className={styles.icon}>
                  <Icon name={item.icon} size={22} />
                </span>
                <span className={styles.label}>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
