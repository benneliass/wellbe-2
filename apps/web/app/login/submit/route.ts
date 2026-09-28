import { loginConfigFromEnv, signInWithPassword, type SignInResult } from "@/lib/server/zitadel-login";

export const dynamic = "force-dynamic";

const STATUS: Record<SignInResult["kind"], number> = {
  ok: 200,
  password_change_required: 200,
  weak_password: 422,
  invalid_credentials: 401,
  locked: 423,
  expired: 410,
  unavailable: 502,
};

function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

/** Same-origin only: the configured public origin, or the forwarded host in dev. */
function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  const allowed = process.env["WELLBE_WEB_ORIGIN"];
  if (allowed) return origin === allowed.replace(/\/+$/, "");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

const str = (v: unknown, max: number) =>
  typeof v === "string" && v.length > 0 && v.length <= max ? v : null;

export async function POST(request: Request): Promise<Response> {
  if (!sameOrigin(request)) return json({ kind: "forbidden" }, 403);
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return json({ kind: "bad_request" }, 415);
  }
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
  if (!authRequestId || !/^V2_\d+$/.test(authRequestId) || !loginName || !password || newPassword === null) {
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
