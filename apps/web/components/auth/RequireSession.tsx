"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/useSession";

/**
 * Guards the workspace shell: an onboarded session is required. Without one, the
 * user is sent back to the front door (no session) or into onboarding (signed in
 * but not yet finalized). There is no auto-login, so deep links never bypass it.
 */
export function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session === null) router.replace("/");
    else if (session && !session.onboarded) router.replace("/onboarding");
  }, [session, router]);

  if (session === undefined) return null;
  if (session === null || !session.onboarded) return null;
  return <>{children}</>;
}
