import { AUTH_REQUEST_ID, isJson, json, sameOrigin } from "@/lib/server/login-request";
import {
  demoLoginNameFromEnv,
  loginConfigFromEnv,
  signInAsDemo,
  type DemoSignInResult,
} from "@/lib/server/zitadel-login";

export const dynamic = "force-dynamic";

const STATUS: Record<DemoSignInResult["kind"], number> = {
  ok: 200,
  expired: 200,
  unavailable: 502,
};

/**
 * "Try the demo": finish the auth request as the shared demo user. The body only
 * carries the auth request id; the user is always the configured demo login.
 */
export async function POST(request: Request): Promise<Response> {
  const loginName = demoLoginNameFromEnv();
  if (!loginName) return json({ kind: "not_found" }, 404);
  if (!sameOrigin(request)) return json({ kind: "forbidden" }, 403);
  if (!isJson(request)) return json({ kind: "bad_request" }, 415);
  const config = loginConfigFromEnv();
  if (!config) return json({ kind: "unavailable" }, 503);

  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return json({ kind: "bad_request" }, 400);
  }
  const authRequestId = body["authRequestId"];
  if (typeof authRequestId !== "string" || authRequestId.length > 200 || !AUTH_REQUEST_ID.test(authRequestId)) {
    return json({ kind: "bad_request" }, 400);
  }

  const result = await signInAsDemo(config, { authRequestId, loginName });
  return json(result, STATUS[result.kind]);
}
