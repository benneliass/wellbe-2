import styles from "./Wordmark.module.css";
import { WELLBE_WORDMARK_PATH } from "./wellbeWordmarkPaths";

export interface WordmarkProps {
  /**
   * Use the serif voice (renders via --wb-font-serif). The design system specimen
   * uses Newsreader; that font is not bundled here, so this falls back to the
   * app's serif stack until/if Newsreader is loaded.
   */
  serif?: boolean;
  /** Italicize the accented "Be". */
  accentItalic?: boolean;
  /** Font size in px (defaults to 32). */
  size?: number;
  className?: string;
}

/** The reference letterforms are outlined so spacing and weight do not depend on fonts. */
export function Wordmark({ serif = false, accentItalic = false, size = 32, className }: WordmarkProps) {
  return (
    <span
      className={className ? `${styles.word} ${className}` : styles.word}
      data-serif={serif || undefined}
      style={{ fontSize: size }}
    >
      {serif || accentItalic ? <>Well<span className={styles.accent} data-italic={accentItalic || undefined}>Be</span></> : <>
        <svg className={styles.outline} viewBox="0 0 78 24" aria-hidden="true" focusable="false">
          <path d={WELLBE_WORDMARK_PATH} fill="currentColor" fillRule="evenodd" />
        </svg>
        <span className={styles.accessible}>WellBe</span>
      </>}
    </span>
  );
}
