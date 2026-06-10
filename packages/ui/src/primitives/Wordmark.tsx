import styles from "./Wordmark.module.css";

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

/** The WellBe wordmark: "Well" in text color, "Be" in brand teal. A reusable brand lockup. */
export function Wordmark({ serif = false, accentItalic = false, size = 32, className }: WordmarkProps) {
  return (
    <span
      className={className ? `${styles.word} ${className}` : styles.word}
      data-serif={serif || undefined}
      style={{ fontSize: size }}
    >
      Well
      <span className={styles.accent} data-italic={accentItalic || undefined}>
        Be
      </span>
    </span>
  );
}
