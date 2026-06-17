import { createWellBeClient, type WellBeClient } from "@wellbe/api-client";
import { getAuthToken, getSession, hasSession } from "./session";

/**
 * Browser-side WellBe API client.
 *
 * Base URL defaults to the local cluster ingress host (api.localhost); override
 * at build time with NEXT_PUBLIC_WELLBE_API_URL.
 *
 * Auth (T0.4 / WEL-151): identity comes from lib/session. Until ZITADEL OIDC
 * lands, the session is resolved from dev headers the backend already understands
 * (X-Wellbe-Actor-Id / X-Wellbe-Patient-Id / X-Wellbe-Actor-Type). getToken is
 * wired now so the OIDC swap is a session.ts-only change. Each request also
 * carries a correlation id for C12 audit/tracing.
 */
const BASE_URL = process.env.NEXT_PUBLIC_WELLBE_API_URL ?? "http://api.localhost";

/** True when a session is configured; surfaced so the UI can prompt sign-in. */
export const devSessionConfigured = hasSession();

let client: WellBeClient | null = null;

export function getApiClient(): WellBeClient {
  if (client) return client;
  const c = createWellBeClient({
    baseUrl: BASE_URL,
    getToken: getAuthToken,
    correlationId: () => `web-${crypto.randomUUID()}`,
  });
  c.use({
    onRequest({ request }) {
      const session = getSession();
      if (session) {
        request.headers.set("X-Wellbe-Actor-Id", session.actorId);
        request.headers.set("X-Wellbe-Patient-Id", session.patientId);
        request.headers.set("X-Wellbe-Actor-Type", session.actorType);
      }
      return request;
    },
  });
  client = c;
  return c;
}
