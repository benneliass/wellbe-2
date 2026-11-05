"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Launcher } from "@/components/launcher/Launcher";
import { enterTechnicalWorkspace, skipGuidedExperience } from "@/lib/experience";
import { useSession } from "@/lib/useSession";
import { EntryScreen } from "./EntryScreen";

/**
 * Decides what the root path shows.
 * Guided experience on (or OIDC): no session shows the front door, and a
 * session that is not onboarded goes to onboarding.
 * Guided experience off, in the dev workspace: open the seeded workspace.
 */
export function RootGate() {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session === undefined) return;
    if (session === null || !session.onboarded) {
      if (enterTechnicalWorkspace()) return;
      if (session && !session.onboarded) router.replace("/onboarding");
    }
  }, [session, router]);

  // undefined = pre-hydration; render nothing to avoid flashing the wrong door.
  if (session === undefined) return null;
  if (session === null) return skipGuidedExperience() ? null : <EntryScreen />;
  if (!session.onboarded) return null;
  return <Launcher />;
}
