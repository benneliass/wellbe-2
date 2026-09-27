import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { json, mockFetch, renderWithQuery, signIn, TEST_PATIENT } from "@/lib/records-test-utils";
import { TriageCheckIn, composeCheckIn } from "./TriageCheckIn";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

const NEW_THREAD = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const EXISTING_THREAD = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";

function thread(id: string, title: string) {
  return {
    schema_version: "c13.health_thread.v1",
    thread_id: id,
    patient_id: TEST_PATIENT,
    title,
    status: "active_unresolved",
    status_version: 1,
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-01T10:00:00Z",
  };
}

function routes(over: Record<string, (req: Request) => Response | Promise<Response>> = {}) {
  return mockFetch({
    "GET /v1/threads": () => json([thread(EXISTING_THREAD, "Headache")]),
    "POST /v1/threads": async (req) => {
      const body = (await req.clone().json()) as { title: string };
      return json(thread(NEW_THREAD, body.title), 201);
    },
    "POST /v1/capture": () =>
      json({ schema_version: "c13.capture.response.v1", capture_id: "cap-1", status: "captured", processing: "pending" }, 201),
    ...over,
  });
}

function calls(fetchMock: ReturnType<typeof mockFetch>, key: string): Request[] {
  return fetchMock.mock.calls
    .map(([input]) => input as Request)
    .filter((r) => `${r.method} ${new URL(r.url).pathname}` === key);
}

function answerAll() {
  fireEvent.change(screen.getByLabelText(/as much or as little/i), {
    target: { value: "Dizzy when I stand up. It passes after a minute." },
  });
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  fireEvent.change(screen.getByLabelText(/for example/i), {
    target: { value: "I never used to feel this" },
  });
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  fireEvent.click(screen.getByRole("radio", { name: "In the last few days" }));
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  fireEvent.click(screen.getByRole("radio", { name: "Some things are harder" }));
  fireEvent.change(screen.getByLabelText(/anything specific/i), { target: { value: "stairs" } });
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  fireEvent.change(screen.getByLabelText(/most like to understand/i), {
    target: { value: "Is this my blood pressure?" },
  });
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
}

describe("TriageCheckIn", () => {
  beforeEach(() => signIn());
  afterEach(() => vi.unstubAllGlobals());

  it("asks one question at a time and needs a few words before moving on", () => {
    const fetchMock = routes();
    renderWithQuery(<TriageCheckIn />);

    expect(screen.getByRole("heading", { name: "What's going on?" })).toBeInTheDocument();
    expect(screen.getByText(/question 1 of 5/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/a few words is enough/i);
    expect(screen.getByRole("heading", { name: "What's going on?" })).toBeInTheDocument();
    expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(0);
  });

  it("always shows the calm backstop and never invents urgency", () => {
    routes();
    renderWithQuery(<TriageCheckIn />);

    const backstop = screen.getByRole("complementary", { name: /if you need help now/i });
    expect(backstop).toHaveTextContent(/doesn't judge how urgent/i);
    expect(backstop).toHaveTextContent(/call your local emergency number/i);
    expect(document.body.textContent).not.toMatch(/urgent care now|act now|you (may )?have\b|abnormal/i);
  });

  it("reviews the user's words verbatim, creates a thread and saves the capture", async () => {
    const fetchMock = routes();
    renderWithQuery(<TriageCheckIn />);
    answerAll();

    expect(screen.getByRole("heading", { name: /here's what you told us/i })).toBeInTheDocument();
    const voice = screen.getByRole("region", { name: /your words/i });
    expect(within(voice).getByText("Dizzy when I stand up. It passes after a minute.")).toBeInTheDocument();
    expect(within(voice).getByText("Some things are harder — stairs")).toBeInTheDocument();

    expect(screen.getByLabelText(/thread name/i)).toHaveValue("Dizzy when I stand up");
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));

    expect(await screen.findByRole("heading", { name: /saved in your own words/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open the thread/i })).toHaveAttribute(
      "href",
      `/threads/${NEW_THREAD}`,
    );

    const [threadReq] = calls(fetchMock, "POST /v1/threads");
    expect(await threadReq!.json()).toEqual({ title: "Dizzy when I stand up" });

    const [captureReq] = calls(fetchMock, "POST /v1/capture");
    expect(captureReq!.headers.get("Idempotency-Key")).toMatch(/[0-9a-f-]{36}/);
    const body = await captureReq!.json();
    expect(body.capture_type).toBe("symptom");
    expect(body.thread_id).toBe(NEW_THREAD);
    expect(body.payload.description).toBe(
      [
        "What's going on: Dizzy when I stand up. It passes after a minute.",
        "Different from my normal: I never used to feel this",
        "Started: In the last few days",
        "Effect on my day: Some things are harder — stairs",
        "Main worry or question: Is this my blood pressure?",
      ].join("\n"),
    );
  });

  it("can attach to an existing thread instead", async () => {
    const fetchMock = routes();
    renderWithQuery(<TriageCheckIn />);
    answerAll();

    fireEvent.click(await screen.findByRole("radio", { name: /a thread i already have/i }));
    fireEvent.change(screen.getByLabelText(/^thread$/i), { target: { value: EXISTING_THREAD } });
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));

    expect(await screen.findByText(/part of “Headache” now/)).toBeInTheDocument();
    expect(calls(fetchMock, "POST /v1/threads")).toHaveLength(0);
    const body = await calls(fetchMock, "POST /v1/capture")[0]!.json();
    expect(body.thread_id).toBe(EXISTING_THREAD);
  });

  it("keeps answers on failure and retries without a duplicate thread or capture key", async () => {
    let attempt = 0;
    const fetchMock = routes({
      "POST /v1/capture": () =>
        ++attempt === 1
          ? json({ detail: "down" }, 503)
          : json({ schema_version: "c13.capture.response.v1", capture_id: "cap-2", status: "captured", processing: "pending" }, 201),
    });
    renderWithQuery(<TriageCheckIn />);
    answerAll();

    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/answers are still here/i);
    expect(screen.getByText("Is this my blood pressure?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });

    expect(calls(fetchMock, "POST /v1/threads")).toHaveLength(1);
    const keys = calls(fetchMock, "POST /v1/capture").map((r) => r.headers.get("Idempotency-Key"));
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });

  it("saves to memory only, without a thread", async () => {
    const fetchMock = routes();
    renderWithQuery(<TriageCheckIn />);
    answerAll();

    fireEvent.click(screen.getByRole("radio", { name: /just save it to my memory/i }));
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));

    await waitFor(() => expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(1));
    expect(calls(fetchMock, "POST /v1/threads")).toHaveLength(0);
    expect((await calls(fetchMock, "POST /v1/capture")[0]!.json()).thread_id).toBeNull();
    expect(await screen.findByRole("link", { name: /back to home/i })).toHaveAttribute("href", "/");
  });

  it("composes only the answers that were given", () => {
    expect(
      composeCheckIn({
        what: " Tired ",
        change: "",
        onset: "",
        onsetNote: "",
        impact: "Not much",
        impactNote: "",
        worry: "",
      }),
    ).toBe("What's going on: Tired\nEffect on my day: Not much");
  });
});
