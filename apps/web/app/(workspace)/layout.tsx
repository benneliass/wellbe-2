import type { ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { RequireSession } from "@/components/auth/RequireSession";

/** Wraps every workspace screen in the persistent nav rail + main column.
 *  Guarded: an onboarded session is required to reach any workspace surface. */
export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <AppShell>{children}</AppShell>
    </RequireSession>
  );
}
