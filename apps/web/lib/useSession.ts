"use client";

import { useSyncExternalStore } from "react";
import { type Session, getSession, subscribeSession } from "./session";

/**
 * Reactive view of the current session. Re-renders on sign-in / sign-out / switch.
 * Returns `undefined` on the server and first client paint (before hydration),
 * so callers can render a neutral "checking" state and never flash the wrong door.
 */
export function useSession(): Session | null | undefined {
  return useSyncExternalStore(
    subscribeSession,
    () => getSession(),
    () => undefined,
  );
}
