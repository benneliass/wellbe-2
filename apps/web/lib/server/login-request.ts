/** Request guards shared by the /login/* route handlers. */

export function json(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

/** Same-origin only: the configured public origin, or the forwarded host in dev. */
export function sameOrigin(request: Request): boolean {
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

export const isJson = (request: Request) =>
  request.headers.get("content-type")?.startsWith("application/json") ?? false;

export const AUTH_REQUEST_ID = /^V2_\d+$/;
