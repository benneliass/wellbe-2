import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { clearSession } from "@/lib/session";
import { PrepareLive } from "./PrepareLive";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

const PACKET_ID = "11111111-1111-4111-8111-111111111111";

function stmt(over: Record<string, unknown>) {
  return {
    statement_id: "s-x",
    layer: "summary",
    section: "concern",
    ordinal: 0,
    text: "",
    classification: "direct_source_fact",
    source_refs: [],
    absent: false,
    absence_reason: null,
    included: true,
    ...over,
  };
}

function packet(statements = defaultStatements()) {
  return {
    packet_id: PACKET_ID,
    patient_id: "p",
    title: "Visit packet",
    status: "draft",
    thread_ids: [],
    statements,
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-01T10:00:00Z",
  };
}

function defaultStatements() {
  return [
    stmt({
      statement_id: "q1",
      layer: "patient_prep",
      section: "question",
      text: "Is it a tear?",
      classification: "patient_reported",
      source_refs: [{ ref_type: "patient_entered", source_id: PACKET_ID, label: "Your question" }],
    }),
    stmt({
      statement_id: "c1",
      layer: "summary",
      section: "concern",
      ordinal: 1,
      text: "Knee pain since May",
      source_refs: [{ ref_type: "health_thread", source_id: "t1", label: "Knee pain" }],
    }),
  ];
}

const THREADS = [
  {
    thread_id: "t1",
    title: "Knee pain",
    status: "active",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  },
];

let shareLinks: unknown[] = [];

function routes(extra: Record<string, (req: Request) => Response | Promise<Response>> = {}) {
  return mockFetch({
    "GET /v1/threads": () => json(THREADS),
    "POST /v2/visit-packets": () => json(packet(), 201),
    "GET /v2/share-links": () => json(shareLinks),
    ...extra,
  });
}

async function buildAndReview() {
  fireEvent.click(await screen.findByRole("button", { name: "Build packet" }));
  await screen.findByText(/2 of 2 items included/);
}

function bodyOf(fetchMock: ReturnType<typeof mockFetch>, method: string, path: string) {
  const call = fetchMock.mock.calls.find(([input]) => {
    const req = input as Request;
    return req.method === method && new URL(req.url).pathname === path;
  });
  return call ? (call[0] as Request).clone().json() : Promise.resolve(undefined);
}

describe("PrepareLive — 3-step visit packet", () => {
  beforeEach(() => {
    signIn();
    shareLinks = [];
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    clearSession();
  });

  it("shows a visible stepper; later steps stay locked until reached", async () => {
    routes();
    renderWithQuery(<PrepareLive />);
    const nav = screen.getByRole("navigation", { name: /visit packet steps/i });
    expect(within(nav).getByText("Choose").closest("[aria-current]")).toHaveAttribute(
      "aria-current",
      "step",
    );
    expect(within(nav).queryByRole("button")).not.toBeInTheDocument();
    await screen.findByRole("button", { name: "Knee pain" });
  });

  it("Step 2 shows each statement with its source and review marker, and says nothing is shared yet", async () => {
    routes();
    renderWithQuery(<PrepareLive />);
    await buildAndReview();

    expect(screen.getByText(/you approve everything before sharing/i)).toBeInTheDocument();
    expect(screen.getByText("Your words")).toBeInTheDocument();
    expect(screen.getByText("Not clinician-reviewed")).toBeInTheDocument();
    expect(screen.getByText("Your question")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /knee pain.*open evidence/i })).toBeInTheDocument();
    // Summary statements can be removed but not reworded.
    expect(screen.getByRole("button", { name: "Edit: Is it a tear?" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit: Knee pain since May" })).toBeNull();

    // Choose is now revisitable from the stepper.
    const nav = screen.getByRole("navigation", { name: /visit packet steps/i });
    expect(within(nav).getByRole("button", { name: /choose/i })).toBeInTheDocument();
  });

  it("removes an item via PATCH inclusions and reflects it in the count", async () => {
    const fetchMock = routes({
      [`PATCH /v2/visit-packets/${PACKET_ID}`]: () => json(packet()),
    });
    renderWithQuery(<PrepareLive />);
    await buildAndReview();

    fireEvent.click(screen.getByRole("button", { name: "Remove: Knee pain since May" }));
    expect(await screen.findByText(/1 of 2 items included/)).toBeInTheDocument();
    expect(screen.getByText(/won.t be shared/i)).toBeInTheDocument();
    await waitFor(async () =>
      expect(await bodyOf(fetchMock, "PATCH", `/v2/visit-packets/${PACKET_ID}`)).toEqual({
        inclusions: [{ statement_id: "c1", included: false }],
      }),
    );
  });

  it("rewords the person's own question via PATCH edits", async () => {
    const edited = defaultStatements();
    edited[0]!.text = "Could it be a tear?";
    const fetchMock = routes({
      [`PATCH /v2/visit-packets/${PACKET_ID}`]: () => json(packet(edited)),
    });
    renderWithQuery(<PrepareLive />);
    await buildAndReview();

    fireEvent.click(screen.getByRole("button", { name: "Edit: Is it a tear?" }));
    fireEvent.change(screen.getByLabelText("Edit this item"), {
      target: { value: "Could it be a tear?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.queryByLabelText("Edit this item")).toBeNull());
    expect(screen.getByText("Could it be a tear?")).toBeInTheDocument();
    expect(await bodyOf(fetchMock, "PATCH", `/v2/visit-packets/${PACKET_ID}`)).toEqual({
      edits: [{ statement_id: "q1", text: "Could it be a tear?" }],
    });
  });

  it("Step 3 shares with recipient type, name, expiry and shows exactly what they can see", async () => {
    const fetchMock = routes({
      [`POST /v2/visit-packets/${PACKET_ID}/share`]: () => {
        shareLinks = [
          {
            share_link_id: "l1",
            packet_id: PACKET_ID,
            packet_title: "Visit packet",
            recipient_name: "Maya (daughter)",
            purpose: "caregiver_support",
            info_scope: "selected_threads",
            status: "active",
            passcode_required: false,
            created_at: "2026-09-27T10:00:00Z",
            expires_at: "2026-09-28T10:00:00Z",
            revoked_at: null,
          },
        ];
        return json(
          {
            share_link_id: "l1",
            grant_id: "g1",
            share_token: "tok-abc",
            passcode_required: false,
            expires_at: "2026-09-28T10:00:00Z",
            c10_decision: "allow",
          },
          201,
        );
      },
      [`POST /v2/visit-packets/${PACKET_ID}/share/l1/revoke`]: () =>
        new Response(null, { status: 204 }),
    });
    renderWithQuery(<PrepareLive />);
    await buildAndReview();
    fireEvent.click(screen.getByRole("button", { name: "Approve and continue" }));

    expect(await screen.findByText("You haven’t shared a packet yet.")).toBeInTheDocument();
    const perms = screen.getByLabelText("What they can see");
    expect(perms).toHaveTextContent(/only the 2 items you approved/i);
    expect(perms).toHaveTextContent(/view only/i);

    fireEvent.click(screen.getByRole("radio", { name: /a caregiver/i }));
    fireEvent.change(screen.getByLabelText("Their name"), { target: { value: "Maya (daughter)" } });
    fireEvent.change(screen.getByLabelText("Access expires"), { target: { value: "24" } });
    fireEvent.click(screen.getByRole("button", { name: "Create link" }));

    expect(await screen.findByText(/\/shared\/tok-abc$/)).toBeInTheDocument();
    expect(await bodyOf(fetchMock, "POST", `/v2/visit-packets/${PACKET_ID}/share`)).toMatchObject({
      recipient_name: "Maya (daughter)",
      purpose: "caregiver_support",
      expires_in_hours: 24,
      passcode: null,
    });

    const active = await screen.findByRole("list", { name: "Active shares" });
    expect(within(active).getByText("Maya (daughter)")).toBeInTheDocument();
    fireEvent.click(
      within(active).getByRole("button", { name: "Revoke access for Maya (daughter)" }),
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input]) =>
          new URL((input as Request).url).pathname.endsWith("/share/l1/revoke"),
        ),
      ).toBe(true),
    );
  });

  it("keeps the person on Step 3 with a plain explanation when the safety check blocks sharing", async () => {
    routes({
      [`POST /v2/visit-packets/${PACKET_ID}/share`]: () =>
        json({ code: "theory_diagnosis_violation" }, 422),
    });
    renderWithQuery(<PrepareLive />);
    await buildAndReview();
    fireEvent.click(screen.getByRole("button", { name: "Approve and continue" }));
    fireEvent.change(await screen.findByLabelText("Their name"), { target: { value: "Dr. Lee" } });
    fireEvent.click(screen.getByRole("button", { name: "Create link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/safety check/i);
    expect(screen.getByRole("button", { name: "Back to review" })).toBeInTheDocument();
  });

  it("requires re-approval after the preview changes", async () => {
    routes({ [`PATCH /v2/visit-packets/${PACKET_ID}`]: () => json(packet()) });
    renderWithQuery(<PrepareLive />);
    await buildAndReview();
    fireEvent.click(screen.getByRole("button", { name: "Approve and continue" }));
    fireEvent.click(await screen.findByRole("button", { name: "Back to review" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove: Knee pain since May" }));
    const nav = screen.getByRole("navigation", { name: /visit packet steps/i });
    expect(within(nav).queryByRole("button", { name: /share/i })).toBeNull();
  });
});
