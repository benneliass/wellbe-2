import styles from "./Tabs.module.css";

export interface TabItem {
  id: string;
  label: string;
  /** Optional count shown beside the label. */
  count?: number;
}

export interface TabsProps {
  items: TabItem[];
  /** Currently active tab id. */
  value: string;
  onChange: (id: string) => void;
}

/** Segmented control for switching views (e.g. All / Active / Needs attention). Controlled. */
export function Tabs({ items, value, onChange }: TabsProps) {
  return (
    <div className={styles.tabs} role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={item.id === value}
          className={styles.tab}
          data-active={item.id === value || undefined}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.count != null && <span className={styles.count}>{item.count}</span>}
        </button>
      ))}
    </div>
  );
}
