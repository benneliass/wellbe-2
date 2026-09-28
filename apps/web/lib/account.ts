"use client";

import { isOidcMode } from "./auth-config";
import { useSession } from "./useSession";

export interface AccountIdentity {
  name: string;
  email: string | null;
  initials: string;
  /** How this session was established, for the account surface. */
  signInMethod: string;
}

export function toInitials(name: string): string {
  const base = name.includes("@") ? (name.split("@")[0] ?? "") : name;
  const parts = base.trim().split(/[\s._-]+/).filter(Boolean).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "Y";
}

/** Who is signed in, as shown in the header, account panel, and switcher. */
export function useAccount(): AccountIdentity {
  const session = useSession();
  const email = session?.email ?? null;
  const name = session?.displayName || email || "You";
  return {
    name,
    email,
    initials: toInitials(name),
    signInMethod: isOidcMode() ? "Signed in with your WellBe login" : "Local dev identity",
  };
}
