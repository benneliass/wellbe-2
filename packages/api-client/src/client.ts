/**
 * Runtime WellBe API client.
 * Thin, typed wrapper over the generated OpenAPI types using openapi-fetch.
 * Handles base URL, auth header injection, and correlation-id passthrough.
 */
import createClient, { type Client } from "openapi-fetch";
import type { paths } from "./generated";

export interface WellBeClientOptions {
  baseUrl: string;
  /** Returns the current bearer token (paired with the frontend auth story, WEL-151). */
  getToken?: () => string | null | undefined | Promise<string | null | undefined>;
  /** Returns a per-request correlation id for tracing/audit (C12). */
  correlationId?: () => string;
}

export type WellBeClient = Client<paths>;

export function createWellBeClient(opts: WellBeClientOptions): WellBeClient {
  const client = createClient<paths>({ baseUrl: opts.baseUrl });

  client.use({
    async onRequest({ request }) {
      const token = await opts.getToken?.();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      const corr = opts.correlationId?.();
      if (corr) request.headers.set("X-Correlation-Id", corr);
      return request;
    },
  });

  return client;
}
