import type { ReactNode } from "react";
import { PageBody } from "@/components/shell/AppShell";
import styles from "./preview.module.css";

/** Public, fixture-only design surfaces; never create a session or load records. */
export default function DesignLayout({ children }: { children: ReactNode }) {
  return <main id="main" className={styles.preview}><PageBody>{children}</PageBody></main>;
}
