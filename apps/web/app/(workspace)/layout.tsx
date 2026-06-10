import type { ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";

/** Wraps every workspace screen in the persistent nav rail + main column. */
export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
