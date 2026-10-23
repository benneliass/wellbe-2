/** Opaque token to session JSON. clear() drops sessions and leaves the graph store alone. */

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

/** Session body held under a token. Not a signed handle claim. */
export type SessionJson = { [key: string]: JsonValue };

export interface SessionStore {
  put(token: string, session: SessionJson): void;
  get(token: string): SessionJson | undefined;
  delete(token: string): void;
  clear(): void;
}

function cloneSession(session: SessionJson): SessionJson {
  return JSON.parse(JSON.stringify(session)) as SessionJson;
}

export class MemorySessionStore implements SessionStore {
  private readonly sessions = new Map<string, SessionJson>();

  put(token: string, session: SessionJson): void {
    this.sessions.set(token, cloneSession(session));
  }

  get(token: string): SessionJson | undefined {
    const session = this.sessions.get(token);
    return session ? cloneSession(session) : undefined;
  }

  delete(token: string): void {
    this.sessions.delete(token);
  }

  /** Reload policy: exploration sessions expire. Durable graph state stays in GraphStore. */
  clear(): void {
    this.sessions.clear();
  }
}
