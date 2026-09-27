import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { ResultsLive } from "./ResultsLive";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

const THREAD_ID = "c2b8ed07-e837-44a4-8ebd-dd1fc5f0879b";
const CAPTURE_OLD = "11111111-1111-4111-8111-111111111111";
const CAPTURE_NEW = "22222222-2222-4222-8222-222222222222";
const DOC_ID = "33333333-3333-4333-8333-333333333333";

function obs(over: Record<string, unknown>) {
  return {
    value: "165",
    unit: "mg/dL",
    numeric_value: 165,
    reference_range: "<130",
    range_position: "outside",
    range_note: "Outside the reference range shown on the report",
    observed_at: "2026-09-27T10:00:00Z",
    source: {
      kind: "entered_by_you",
      display_label: "Entered by you",
      capture_id: CAPTURE_NEW,
      document_id: null,
      review_marker: "patient-entered",
    },
    ...over,
  };
}

const ldlOld = obs({
  value: "150",
  numeric_value: 150,
  observed_at: "2026-06-03T10:00:00Z",
  source: {
    kind: "document",
    display_label: "From a PDF you added",
    capture_id: CAPTURE_OLD,
    document_id: DOC_ID,
    review_marker: "not-clinician-reviewed",
  },
});
const ldlNew = obs({});
const vitD = obs({
  value: "45",
  unit: "ng/mL",
  numeric_value: 45,
  reference_range: "30-100",
  range_position: "within",
  range_note: "Within the reference range shown on the report",
  observed_at: "2026-09-20T10:00:00Z",
});

const RESULTS = {
  schema_version: "c13.results.v2",
  headline: "2 kinds of result in your records",
  note: "Values and reference ranges are shown exactly as your sources gave them.",
  not_diagnosis: true,
  analytes: [
    {
      analyte_key: "lab:ldl_cholesterol",
      display_label: "LDL cholesterol",
      kind: "lab",
      latest: ldlNew,
      history: [ldlOld, ldlNew],
      threads: [{ thread_id: THREAD_ID, title: "LDL cholesterol" }],
    },
    {
      analyte_key: "lab:vitamin_d",
      display_label: "Vitamin D (25-OH)",
      kind: "lab",
      latest: vitD,
      history: [vitD],
      threads: [],
    },
  ],
};

describe("ResultsLive", () => {
  beforeEach(() => signIn());
  afterEach(() => vi.unstubAllGlobals());

  it("shows each analyte's latest value, calm range note, source and thread link", async () => {
    const fetchMock = mockFetch({ "GET /v2/results": () => json(RESULTS) });
    renderWithQuery(<ResultsLive />);

    expect(screen.getByRole("status")).toHaveTextContent(/gathering your results/i);
    const list = await screen.findByRole("list", { name: /your results/i });
    const ldl = within(list).getByRole("listitem", { name: "LDL cholesterol" });

    expect(within(ldl).getByText("165")).toBeInTheDocument();
    expect(within(ldl).getByText(/outside the reference range shown on the report/i)).toBeInTheDocument();
    expect(within(ldl).getByText(/range shown: <130/i)).toBeInTheDocument();
    expect(within(ldl).getByText(/higher than the previous reading \(150 mg\/dL/i)).toBeInTheDocument();
    expect(within(ldl).getByText("Entered by you")).toBeInTheDocument();
    expect(within(ldl).getByRole("link", { name: /in your thread: ldl cholesterol/i })).toHaveAttribute(
      "href",
      `/threads/${THREAD_ID}`,
    );

    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/abnormal|diagnos/i);
    expect(text).not.toContain(CAPTURE_NEW);
    expect(text).not.toContain(THREAD_ID);

    const [req] = fetchMock.mock.calls[0]!;
    expect(new URL((req as Request).url).pathname).toBe("/v2/results");
  });

  it("keeps the full trend collapsed until asked, then shows every reading", async () => {
    mockFetch({ "GET /v2/results": () => json(RESULTS) });
    renderWithQuery(<ResultsLive />);

    const toggle = await screen.findByRole("button", { name: /show all 2 readings/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const table = screen.getByRole("table", { name: /all readings of ldl cholesterol/i });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1]!).getByText("150 mg/dL")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("From a PDF you added")).toBeInTheDocument();
    expect(within(rows[2]!).getByText("165 mg/dL")).toBeInTheDocument();
  });

  it("filters to one document's results when linked from Documents", async () => {
    mockFetch({ "GET /v2/results": () => json(RESULTS) });
    renderWithQuery(<ResultsLive documentId={DOC_ID} />);

    expect(await screen.findByRole("heading", { name: /results found in one document/i })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: "LDL cholesterol" })).toBeInTheDocument();
    expect(screen.queryByRole("listitem", { name: /vitamin d/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /show all results/i })).toHaveAttribute("href", "/results");
  });

  it("shows a calm empty state", async () => {
    mockFetch({
      "GET /v2/results": () =>
        json({ ...RESULTS, analytes: [], headline: "No results yet", note: "Add one any time." }),
    });
    renderWithQuery(<ResultsLive />);
    expect(await screen.findByRole("heading", { name: "No results yet" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Add your first result" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add a result/i })).toBeInTheDocument();
  });

  it("shows a calm error with a retry that recovers", async () => {
    let calls = 0;
    mockFetch({
      "GET /v2/results": () => (++calls === 1 ? json({ detail: "boom" }, 500) : json(RESULTS)),
    });
    renderWithQuery(<ResultsLive />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/couldn't load your results/i);
    fireEvent.click(within(alert).getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("listitem", { name: "LDL cholesterol" })).toBeInTheDocument();
  });

  it("opens the existing Capture modal on the lab type", async () => {
    mockFetch({ "GET /v2/results": () => json(RESULTS) });
    renderWithQuery(<ResultsLive />);

    fireEvent.click(await screen.findByRole("button", { name: /add a result/i }));
    await waitFor(() => expect(screen.getByLabelText(/test name/i)).toBeInTheDocument());
  });
});
