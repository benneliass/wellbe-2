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

type Route = "route_routine" | "route_soon" | "route_urgent";

const GUIDANCE: Record<Route, { template_id: string; headline: string; action: string; rationale: string; backstop: string }> = {
  route_routine: {
    template_id: "routine.v1",
    headline: "Saved for you to follow over time",
    action: "WellBe will keep this with your notes.",
    rationale: "Nothing you wrote matched the warning signs WellBe checks for.",
    backstop: "This list isn't complete. If you think it's an emergency, call your local emergency number.",
  },
  route_soon: {
    template_id: "same_day.v1",
    headline: "Please contact a clinician today",
    action: "Reach your doctor, a nurse line or an urgent care service today.",
    rationale: "Some of what you wrote is worth a same-day check.",
    backstop: "If things get worse, call your local emergency number.",
  },
  route_urgent: {
    template_id: "emergency_now.v1",
    headline: "Please get emergency help now",
    action: "Call 911 now, or ask someone nearby to call for you. If you can, don't drive yourself.",
    rationale: "Some of what you wrote can be a sign that needs checking straight away.",
    backstop: "Your answers are still here. You can save your check-in afterwards.",
  },
};

function evaluation(route: Route, over: Record<string, unknown> = {}) {
  return {
    schema_version: "c13.triage.evaluate.v2",
    evaluation_id: "ev-1",
    evaluated_at: "2026-09-28T10:00:00Z",
    route,
    safety_gate_decision: route === "route_urgent" ? "route_urgent" : "allow_with_obligations",
    crisis_support: false,
    matched_rules: [],
    guidance: {
      ...GUIDANCE[route],
      emergency_number: route === "route_urgent" ? "911" : null,
      crisis_line: null,
    },
    sources: [],
    jurisdiction: "US",
    ruleset_version: "2026.09-starter.1",
    clinical_review_status: "pending_clinical_review",
    not_diagnosis: true,
    ...over,
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
    "POST /v2/triage/evaluate": () => json(evaluation("route_routine")),
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
    expect(backstop).toHaveTextContent(/short list of warning signs/i);
    expect(backstop).toHaveTextContent(/isn't a diagnosis/i);
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

  it("checks for warning signs before saving and sends the answers", async () => {
    const fetchMock = routes();
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });

    const order = fetchMock.mock.calls.map(([input]) => {
      const r = input as Request;
      return `${r.method} ${new URL(r.url).pathname}`;
    });
    expect(order.indexOf("POST /v2/triage/evaluate")).toBeGreaterThanOrEqual(0);
    expect(order.indexOf("POST /v2/triage/evaluate")).toBeLessThan(order.indexOf("POST /v1/threads"));
    const [evalReq] = calls(fetchMock, "POST /v2/triage/evaluate");
    expect(await evalReq!.json()).toEqual({
      schema_version: "c13.triage.evaluate.request.v2",
      answers: {
        what: "Dizzy when I stand up. It passes after a minute.",
        change: "I never used to feel this",
        onset: "In the last few days",
        onset_note: "",
        impact: "Some things are harder",
        impact_note: "stairs",
        worry: "Is this my blood pressure?",
      },
    });
    expect(document.querySelector('[data-state="urgent"]')).toBeNull();
    expect(document.querySelector('[data-state="needs_attention"]')).toBeNull();
  });

  it("stops before saving and shows urgent guidance calmly only for route_urgent", async () => {
    const fetchMock = routes({ "POST /v2/triage/evaluate": () => json(evaluation("route_urgent")) });
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));

    const heading = await screen.findByRole("heading", { name: "Please get emergency help now" });
    const card = heading.closest("section")!;
    expect(card).toHaveAttribute("data-state", "urgent");
    expect(within(card).getByText(/call 911 now/i)).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Call 911" })).toHaveAttribute("href", "tel:911");
    expect(card.textContent).not.toMatch(/!|you (may )?have\b|diagnos/i);
    expect(calls(fetchMock, "POST /v1/threads")).toHaveLength(0);
    expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(0);

    fireEvent.click(within(card).getByRole("button", { name: /save my check-in anyway/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });
    expect(calls(fetchMock, "POST /v2/triage/evaluate")).toHaveLength(1);
    expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(1);
    expect(document.querySelector('[data-state="urgent"]')).toBeNull();
  });

  it("goes back to the answers from urgent guidance and re-checks after an edit", async () => {
    const fetchMock = routes({ "POST /v2/triage/evaluate": () => json(evaluation("route_urgent")) });
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    fireEvent.click(await screen.findByRole("button", { name: /back to my answers/i }));
    expect(screen.getByRole("heading", { name: /here's what you told us/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Edit: Main worry or question" }));
    fireEvent.change(screen.getByLabelText(/most like to understand/i), { target: { value: "Why?" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: "Please get emergency help now" });
    expect(calls(fetchMock, "POST /v2/triage/evaluate")).toHaveLength(2);
  });

  it("never shows red when the Safety Gate did not approve route_urgent", async () => {
    const fetchMock = routes({
      "POST /v2/triage/evaluate": () =>
        json(evaluation("route_urgent", { safety_gate_decision: "allow_with_obligations" })),
    });
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });
    expect(document.querySelector('[data-state="urgent"]')).toBeNull();
    expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(1);
  });

  it("saves and shows same-day guidance in the attention tone for route_soon", async () => {
    routes({ "POST /v2/triage/evaluate": () => json(evaluation("route_soon")) });
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });
    const note = screen.getByRole("complementary", { name: "Please contact a clinician today" });
    expect(note).toHaveAttribute("data-state", "needs_attention");
    expect(document.querySelector('[data-state="urgent"]')).toBeNull();
  });

  it("still saves when the check is unavailable, and says so calmly", async () => {
    const fetchMock = routes({ "POST /v2/triage/evaluate": () => json({ detail: "down" }, 503) });
    renderWithQuery(<TriageCheckIn />);
    answerAll();
    fireEvent.click(screen.getByRole("button", { name: /save my check-in/i }));
    await screen.findByRole("heading", { name: /saved in your own words/i });
    expect(calls(fetchMock, "POST /v1/capture")).toHaveLength(1);
    const note = screen.getByRole("complementary", { name: /about warning signs/i });
    expect(note).toHaveTextContent(/couldn't check your words for warning signs/i);
    expect(note).toHaveAttribute("data-state", "needs_attention");
    expect(document.querySelector('[data-state="urgent"]')).toBeNull();
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
