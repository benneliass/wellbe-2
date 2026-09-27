import { parseAuthMode } from "@/lib/auth-config";

// Read per request from the container env, so one image serves every target.
export const dynamic = "force-dynamic";

function runtimeEnv(name: string): string {
  // Indexed access keeps Next from inlining the build-time value.
  return process.env[name] ?? "";
}

export function GET(): Response {
  const config = {
    mode: parseAuthMode(runtimeEnv("NEXT_PUBLIC_WELLBE_AUTH_MODE")),
    issuer: runtimeEnv("NEXT_PUBLIC_WELLBE_OIDC_ISSUER"),
    clientId: runtimeEnv("NEXT_PUBLIC_WELLBE_OIDC_CLIENT_ID"),
  };
  const json = JSON.stringify(config).replace(/</g, "\\u003c");
  return new Response(`window.__WELLBE_AUTH_CONFIG__ = ${json};\n`, {
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
