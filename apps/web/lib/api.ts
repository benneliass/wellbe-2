import { createWellBeClient, type WellBeClient } from "@wellbe/api-client";

/**
 * Browser-side WellBe API client.
 *
 * Base URL defaults to the local cluster ingress host (api.localhost); override
 * at build time with NEXT_PUBLIC_WELLBE_API_URL.
 *
 * Auth (T0.4 / WEL-151): the backend's resolve_principal accepts the dev headers
 * X-Wellbe-Actor-Id / X-Wellbe-Patient-Id. Until real ZITADEL OIDC lands, a dev
 * session id can be injected via NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID /
 * NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID so the read endpoints are reachable. This
 * only sends headers the API already understands — it does not change C1 logic.
 */
const BASE_URL = process.env.NEXT_PUBLIC_WELLBE_API_URL ?? "http://api.localhost";
const DEV_ACTOR_ID = process.env.NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID ?? "";
const DEV_PATIENT_ID = process.env.NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID ?? "";

/** True when a dev session is configured; surfaced so the UI can prompt sign-in. */
export const devSessionConfigured = Boolean(DEV_ACTOR_ID);

let client: WellBeClient | null = null;

export function getApiClient(): WellBeClient {
  if (client) return client;
  const c = createWellBeClient({ baseUrl: BASE_URL });
  c.use({
    onRequest({ request }) {
      if (DEV_ACTOR_ID) request.headers.set("X-Wellbe-Actor-Id", DEV_ACTOR_ID);
      if (DEV_PATIENT_ID) request.headers.set("X-Wellbe-Patient-Id", DEV_PATIENT_ID);
      return request;
    },
  });
  client = c;
  return c;
}
