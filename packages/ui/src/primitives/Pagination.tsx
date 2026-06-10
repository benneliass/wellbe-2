import { Icon } from "../Icon";
import styles from "./Pagination.module.css";

export interface PaginationProps {
  /** Current page, 1-based. */
  page: number;
  /** Total number of pages. */
  pageCount: number;
  onChange: (page: number) => void;
  /** Pages to show on each side of the current page (default 1). */
  siblingCount?: number;
}

type PageItem = number | "ellipsis";

function buildRange(page: number, pageCount: number, siblingCount: number): PageItem[] {
  if (pageCount <= 1) return pageCount === 1 ? [1] : [];
  const first = 1;
  const last = pageCount;
  const start = Math.max(page - siblingCount, first);
  const end = Math.min(page + siblingCount, last);

  const items: PageItem[] = [first];
  if (start > first + 1) items.push("ellipsis");
  for (let p = start; p <= end; p += 1) {
    if (p !== first && p !== last) items.push(p);
  }
  if (end < last - 1) items.push("ellipsis");
  if (last !== first) items.push(last);
  return items;
}

/** Numbered pagination with prev/next chevrons and ellipsis collapsing. Controlled. */
export function Pagination({ page, pageCount, onChange, siblingCount = 1 }: PaginationProps) {
  const items = buildRange(page, pageCount, siblingCount);
  return (
    <nav className={styles.pg} aria-label="Pagination">
      <button
        type="button"
        className={styles.num}
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        <Icon name="chevron-left" size={15} />
      </button>
      {items.map((item, i) =>
        item === "ellipsis" ? (
          <span key={`e${i}`} className={styles.ellipsis} aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            className={styles.num}
            data-active={item === page || undefined}
            aria-current={item === page ? "page" : undefined}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ),
      )}
      <button
        type="button"
        className={styles.num}
        onClick={() => onChange(page + 1)}
        disabled={page >= pageCount}
        aria-label="Next page"
      >
        <Icon name="chevron-right" size={15} />
      </button>
    </nav>
  );
}
