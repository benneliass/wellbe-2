import { AUTH_REQUEST_ID, isJson, json, sameOrigin } from "@/lib/server/login-request";
import { loginConfigFromEnv, signInWithPassword, type SignInResult } from "@/lib/server/zitadel-login";

export const dynamic = "force-dynamic";

// Outcomes of the form itself are 200 with a `kind` (browsers log every non-2xx
// fetch as a console error); only protocol errors and outages are non-2xx.
const STATUS: Record<SignInResult["kind"], number> = {
  ok: 200,
  password_change_required: 200,
  weak_password: 200,
  invalid_credentials: 200,
  locked: 200,
  expired: 200,
  unavailable: 502,
};

const str = (v: unknown, max: number) =>
  typeof v === "string" && v.length > 0 && v.length <= max ? v : null;

export async function POST(request: Request): Promise<Response> {
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
  const authRequestId = str(body["authRequestId"], 200);
  const loginName = str(body["loginName"], 320);
  const password = str(body["password"], 256);
  const newPassword = body["newPassword"] === undefined ? undefined : str(body["newPassword"], 256);
  if (!authRequestId || !AUTH_REQUEST_ID.test(authRequestId) || !loginName || !password || newPassword === null) {
    return json({ kind: "bad_request" }, 400);
  }

  const result = await signInWithPassword(config, {
    authRequestId,
    loginName: loginName.trim(),
    password,
    newPassword,
  });
  return json(result, STATUS[result.kind]);
}
