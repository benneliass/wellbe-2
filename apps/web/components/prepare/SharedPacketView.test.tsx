import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { json, mockFetch } from "@/lib/records-test-utils";
import { SharedPacketView } from "./SharedPacketView";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

describe("SharedPacketView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows only the shared statements, each with a readable source marker", async () => {
    mockFetch({
      "GET /v2/share/tok": () =>
        json({
          title: "Visit packet",
          statements: [
            {
              statement_id: "q1",
              layer: "patient_prep",
              section: "question",
              ordinal: 0,
              text: "Is it a tear?",
              classification: "patient_reported",
              source_refs: [{ ref_type: "patient_entered", source_id: "x", label: "Your question" }],
              absent: false,
              included: true,
            },
          ],
          expires_at: "2026-10-01T10:00:00Z",
          review_note: "Patient-prepared and not clinician-reviewed.",
        }),
    });
    render(<SharedPacketView token="tok" />);
    expect(await screen.findByRole("heading", { level: 1, name: "Visit packet" })).toBeVisible();
    expect(screen.getByText("Is it a tear?")).toBeInTheDocument();
    expect(screen.getByText("Patient's words")).toBeInTheDocument();
    expect(screen.getByText("Your question")).toBeInTheDocument();
    expect(screen.getByText(/not clinician-reviewed/i)).toBeInTheDocument();
  });

  it("asks for a passcode when the first open is refused", async () => {
    mockFetch({ "GET /v2/share/tok": () => json({ detail: "gone" }, 404) });
    render(<SharedPacketView token="tok" />);
    expect(await screen.findByRole("heading", { name: /enter the passcode/i })).toBeVisible();
    expect(screen.getByPlaceholderText("Passcode")).toBeInTheDocument();
  });
});
