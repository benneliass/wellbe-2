import { createWellBeClient, type WellBeClient } from "@wellbe/api-client";
import { isOidcMode } from "./auth-config";
import { clearSession, getAuthToken, getSession, updateSession } from "./session";

/**
 * Browser-side WellBe API client.
 *
 * Base URL defaults to the local cluster ingress host (api.localhost); override
 * at build time with NEXT_PUBLIC_WELLBE_API_URL.
 *
 * Auth (WEL-151), per lib/auth-config mode:
 *  - dev:  every request carries the federated identity (X-Wellbe-Issuer /
 *          X-Wellbe-Subject) the backend's dev-headers adapter understands, plus
 *          the patient/controller headers once onboarding resolved a patient id.
 *  - oidc: only `Authorization: Bearer <access token>` — the API derives the
 *          identity from the verified token and ignores X-Wellbe-* identity
 *          headers, so none are sent.
 * Each request also carries a correlation id for C12 audit/tracing.
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
      if (isOidcMode()) return request;
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
    async onResponse({ response }) {
      if (!isOidcMode() || !getSession()) return response;
      if (response.status === 401) {
        // Token rejected (expired and not refreshable, or revoked): back to sign-in.
        clearSession();
      } else if (response.status === 403) {
        const body = (await response
          .clone()
          .json()
          .catch(() => null)) as { code?: string } | null;
        if (body?.code === "onboarding_required") {
          updateSession({ onboarded: false, patientId: null });
        }
      }
      return response;
    },
  });
  client = c;
  return c;
}
