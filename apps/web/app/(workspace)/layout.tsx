import type { ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { RequireSession } from "@/components/auth/RequireSession";

/** Wraps every workspace screen in the persistent nav rail + main column.
 *  An onboarded session is required. With the guided experience off, the seeded
 *  dev workspace satisfies that without the front door or the wizard. */
export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession>
      <AppShell>{children}</AppShell>
    </RequireSession>
  );
}
