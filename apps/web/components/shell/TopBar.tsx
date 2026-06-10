import Link from "next/link";
import { Icon } from "@wellbe/ui";
import styles from "./TopBar.module.css";

export interface TopBarProps {
  title: string;
  subtitle?: string;
  breadcrumb?: string;
  /** When set, shows a back button linking here. */
  backHref?: string;
}

export function TopBar({ title, subtitle, breadcrumb, backHref }: TopBarProps) {
  return (
    <header className={styles.top}>
      <div className={styles.lead}>
        {backHref && (
          <Link href={backHref} className={styles.back} aria-label="Back">
            <Icon name="arrow-left" size={18} />
          </Link>
        )}
        <div>
          {breadcrumb && <div className={styles.crumb}>{breadcrumb}</div>}
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <div className={styles.sub}>{subtitle}</div>}
        </div>
      </div>
      <div className={styles.tools}>
        <div className={styles.search}>
          <Icon name="search" size={16} />
          <input placeholder="Search threads, labs, notes…" aria-label="Search" />
        </div>
        <button type="button" className={styles.iconbtn} title="Notifications" aria-label="Notifications">
          <Icon name="bell" size={18} />
          <span className={styles.iconbtnDot} />
        </button>
        <button type="button" className={styles.iconbtn} title="Help" aria-label="Help">
          <Icon name="help-circle" size={18} />
        </button>
      </div>
    </header>
  );
}
