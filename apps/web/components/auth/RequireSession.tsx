"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { enterTechnicalWorkspace } from "@/lib/experience";
import { useSession } from "@/lib/useSession";

/**
 * Guards the workspace shell. An onboarded session is required.
 * With the guided experience on, a missing session returns to the front door
 * and an unfinished account goes to onboarding.
 * With it off, the seeded dev workspace is opened instead of those steps.
 * OIDC sign-in is never skipped.
 */
export function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session === undefined) return;
    if (session === null || !session.onboarded) {
      if (enterTechnicalWorkspace()) return;
      router.replace(session === null ? "/" : "/onboarding");
    }
  }, [session, router]);

  if (session === undefined) return null;
  if (session === null || !session.onboarded) return null;
  return <>{children}</>;
}
