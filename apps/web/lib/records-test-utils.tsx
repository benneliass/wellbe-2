import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { vi } from "vitest";
import { setSession } from "./session";

export const TEST_PATIENT = "de7a0000-0000-4000-8000-000000000001";

type Handler = (req: Request) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Stub global fetch with a tiny router keyed by "METHOD /path". Unknown routes
 * answer 404 so a test never silently reaches the network.
 */
export function mockFetch(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const req = input instanceof Request ? input : new Request(input, init);
    const handler = routes[`${req.method} ${new URL(req.url).pathname}`];
    return handler ? handler(req) : json({ detail: "not found" }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function signIn() {
  setSession({
    issuer: "dev-local",
    subject: "dev-controller",
    patientId: TEST_PATIENT,
    actorType: "controller",
    onboarded: true,
    displayName: null,
  });
}

export function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}
