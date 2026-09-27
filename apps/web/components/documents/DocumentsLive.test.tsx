import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { DocumentsLive } from "./DocumentsLive";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

const PROCESSED_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const WAITING_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const UNREADABLE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

function doc(over: Record<string, unknown>) {
  return {
    document_id: PROCESSED_ID,
    display_label: "PDF document from City Lab",
    type_label: "PDF",
    mime_type: "application/pdf",
    added_at: "2026-09-20T10:00:00Z",
    status: "processed",
    status_label: "Processed",
    status_detail: "WellBe read this and found 4 things to keep.",
    extracted_total: 4,
    extracted: [
      { kind: "lab_result", label: "lab results", count: 3 },
      { kind: "symptom", label: "symptom", count: 1 },
    ],
    result_count: 3,
    ...over,
  };
}

const DOCUMENTS = {
  schema_version: "c13.documents.v2",
  headline: "3 documents you've added",
  note: "Originals are stored unchanged.",
  documents: [
    doc({
      document_id: WAITING_ID,
      display_label: "Photo of a document",
      type_label: "Photo",
      mime_type: "image/jpeg",
      status: "waiting",
      status_label: "Waiting to be read",
      status_detail: "WellBe hasn't finished reading this yet.",
      extracted_total: 0,
      extracted: [],
      result_count: 0,
    }),
    doc({}),
    doc({
      document_id: UNREADABLE_ID,
      display_label: "PDF document",
      status: "could_not_read",
      status_label: "Could not be read",
      status_detail: "WellBe couldn't find readable text in this document.",
      extracted_total: 0,
      extracted: [],
      result_count: 0,
    }),
  ],
};

describe("DocumentsLive", () => {
  beforeEach(() => signIn());
  afterEach(() => vi.unstubAllGlobals());

  it("lists documents with type, date and processing status in plain words", async () => {
    mockFetch({ "GET /v2/documents": () => json(DOCUMENTS) });
    renderWithQuery(<DocumentsLive />);

    const list = await screen.findByRole("list", { name: /your documents/i });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);

    const processed = within(list).getByRole("listitem", { name: "PDF document from City Lab" });
    expect(within(processed).getByText(/^Processed\.$/)).toBeInTheDocument();
    expect(within(processed).getByText("PDF")).toBeInTheDocument();
    expect(within(processed).getByText(/3 lab results, 1 symptom/)).toBeInTheDocument();
    expect(
      within(processed).getByRole("link", { name: /see 3 results from this document/i }),
    ).toHaveAttribute("href", `/results?document=${PROCESSED_ID}`);

    expect(within(list).getByText(/^Waiting to be read\.$/)).toBeInTheDocument();
    expect(within(list).getByText(/^Could not be read\.$/)).toBeInTheDocument();
    expect(
      within(within(list).getByRole("listitem", { name: "PDF document" })).queryByRole("link"),
    ).not.toBeInTheDocument();

    expect(document.body.textContent).not.toContain(PROCESSED_ID);
  });

  it("opens the existing Capture modal on the document type", async () => {
    mockFetch({ "GET /v2/documents": () => json(DOCUMENTS) });
    renderWithQuery(<DocumentsLive />);

    fireEvent.click(await screen.findByRole("button", { name: /add a document/i }));
    await waitFor(() => expect(screen.getByText(/click to browse/i)).toBeInTheDocument());
  });

  it("shows a calm empty state with the upload entry point", async () => {
    mockFetch({
      "GET /v2/documents": () =>
        json({ ...DOCUMENTS, documents: [], headline: "No documents yet", note: "Add one." }),
    });
    renderWithQuery(<DocumentsLive />);

    expect(await screen.findByRole("heading", { name: "No documents yet" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Add your first document" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add a document/i })).toBeInTheDocument();
  });

  it("shows a calm error with a retry", async () => {
    let calls = 0;
    mockFetch({
      "GET /v2/documents": () => (++calls === 1 ? json({ detail: "x" }, 503) : json(DOCUMENTS)),
    });
    renderWithQuery(<DocumentsLive />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/couldn't load your documents/i);
    fireEvent.click(within(alert).getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("list", { name: /your documents/i })).toBeInTheDocument();
  });
});
