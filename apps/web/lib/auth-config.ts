/**
 * Auth runtime configuration.
 *
 * NEXT_PUBLIC_* values are inlined at build time, but one web image serves both
 * the dev-header cluster and the OIDC homeserver. So the auth settings are read
 * from the *server's* runtime env by the /auth-config.js route and published on
 * window before hydration (see app/layout.tsx). The build-time NEXT_PUBLIC values
 * are only a fallback (next dev, unit tests).
 */

export type AuthMode = "dev" | "oidc";

export interface AuthConfig {
  mode: AuthMode;
  /** OIDC issuer (ZITADEL external URL), e.g. https://wellbe-auth.<tailnet>.ts.net */
  issuer: string;
  /** Public (PKCE, no secret) client id of the wellbe-web app. */
  clientId: string;
  /** The server offers "Try the demo" (POST /login/demo). Runtime config only. */
  demo: boolean;
}

declare global {
  interface Window {
    __WELLBE_AUTH_CONFIG__?: Partial<AuthConfig>;
  }
}

export function parseAuthMode(value: string | undefined | null): AuthMode {
  return value === "oidc" ? "oidc" : "dev";
}

function buildTimeConfig(): AuthConfig {
  return {
    mode: parseAuthMode(process.env.NEXT_PUBLIC_WELLBE_AUTH_MODE),
    issuer: process.env.NEXT_PUBLIC_WELLBE_OIDC_ISSUER ?? "",
    clientId: process.env.NEXT_PUBLIC_WELLBE_OIDC_CLIENT_ID ?? "",
    demo: false,
  };
}

export function getAuthConfig(): AuthConfig {
  const fallback = buildTimeConfig();
  const runtime = typeof window !== "undefined" ? window.__WELLBE_AUTH_CONFIG__ : undefined;
  if (!runtime) return fallback;
  return {
    mode: parseAuthMode(runtime.mode ?? fallback.mode),
    issuer: runtime.issuer || fallback.issuer,
    clientId: runtime.clientId || fallback.clientId,
    demo: runtime.demo === true,
  };
}

export function isOidcMode(): boolean {
  return getAuthConfig().mode === "oidc";
}

/** OIDC mode with an issuer + client id — i.e. sign-in can actually start. */
export function oidcConfigured(): boolean {
  const cfg = getAuthConfig();
  return cfg.mode === "oidc" && cfg.issuer !== "" && cfg.clientId !== "";
}

/** "Try the demo" can be offered: OIDC sign-in works and the server enabled it. */
export function demoSignInAvailable(): boolean {
  return oidcConfigured() && getAuthConfig().demo;
}
