import { forwardRef, type InputHTMLAttributes } from "react";
import { Icon } from "../Icon";
import styles from "./SearchInput.module.css";

export interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Leading icon (kebab-case lucide name). Defaults to "search". */
  icon?: string;
  /** Class applied to the wrapping field. */
  wrapperClassName?: string;
}

/** Search field with a leading icon. Spread input props (value/onChange/placeholder…) as needed. */
export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  { icon = "search", wrapperClassName, placeholder = "Search…", ...rest },
  ref,
) {
  return (
    <div className={wrapperClassName ? `${styles.search} ${wrapperClassName}` : styles.search}>
      <Icon name={icon} size={16} />
      <input ref={ref} type="search" className={styles.input} placeholder={placeholder} {...rest} />
    </div>
  );
});
