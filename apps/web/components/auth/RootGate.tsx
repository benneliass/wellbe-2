"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Launcher } from "@/components/launcher/Launcher";
import { useSession } from "@/lib/useSession";
import { EntryScreen } from "./EntryScreen";

/**
 * Decides what the root path shows, with no auto-login:
 *  - no session            -> the front door (EntryScreen)
 *  - session, not onboarded -> redirect into onboarding
 *  - onboarded session      -> the calm Launcher home
 */
export function RootGate() {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session && !session.onboarded) router.replace("/onboarding");
  }, [session, router]);

  // undefined = pre-hydration; render nothing to avoid flashing the wrong door.
  if (session === undefined) return null;
  if (session === null) return <EntryScreen />;
  if (!session.onboarded) return null;
  return <Launcher />;
}
