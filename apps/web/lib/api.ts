import { createWellBeClient, type WellBeClient } from "@wellbe/api-client";
import { getAuthToken, getSession } from "./session";

/**
 * Browser-side WellBe API client.
 *
 * Base URL defaults to the local cluster ingress host (api.localhost); override
 * at build time with NEXT_PUBLIC_WELLBE_API_URL.
 *
 * Auth (WEL-151): identity comes from lib/session. Every request carries the
 * federated identity (X-Wellbe-Issuer / X-Wellbe-Subject) the backend's
 * resolve_identity understands, plus the patient/controller headers once
 * onboarding has resolved a patient id. getToken is wired now so a real OIDC
 * id-token is a session.ts-only change. Each request also carries a correlation
 * id for C12 audit/tracing.
 */
const BASE_URL = process.env.NEXT_PUBLIC_WELLBE_API_URL ?? "http://api.localhost";

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
        // Federated identity — present from sign-in, even before onboarding.
        request.headers.set("X-Wellbe-Issuer", session.issuer);
        request.headers.set("X-Wellbe-Subject", session.subject);
        if (session.displayName) {
          request.headers.set("X-Wellbe-Display-Name", session.displayName);
        }
        // Patient/controller identity — only once onboarding has resolved it.
        if (session.patientId) {
          request.headers.set("X-Wellbe-Actor-Id", session.patientId);
          request.headers.set("X-Wellbe-Patient-Id", session.patientId);
          request.headers.set("X-Wellbe-Actor-Type", session.actorType);
        }
      }
      return request;
    },
  });
  client = c;
  return c;
}
