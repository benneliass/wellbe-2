import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Icon } from "../Icon";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "tertiary" | "ghost";

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  icon?: string;
  iconRight?: string;
  full?: boolean;
  children?: ReactNode;
}

/** The shared button. Variants cover primary/secondary/tertiary actions + ghost affordances. */
export function Button({
  variant = "primary",
  size = "md",
  icon,
  iconRight,
  full,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      className={styles.btn}
      data-variant={variant}
      data-size={size}
      data-full={full || undefined}
      {...rest}
    >
      {icon && <Icon name={icon} size={size === "sm" ? 15 : 17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={15} />}
    </button>
  );
}
