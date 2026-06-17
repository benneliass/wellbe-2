import { describe, expect, it } from "vitest";
import type { components } from "@wellbe/api-client";
import { formatShortDate, mapThreadStatus, toThreadSummary } from "./adapters";

type ThreadV1 = components["schemas"]["ThreadV1"];

describe("mapThreadStatus", () => {
  it("maps known HealthThreadStatus values to UI statuses", () => {
    expect(mapThreadStatus("active_unresolved")).toBe("active");
    expect(mapThreadStatus("waiting_for_result")).toBe("monitoring");
    expect(mapThreadStatus("escalated")).toBe("attention");
    expect(mapThreadStatus("explained")).toBe("resolved");
    expect(mapThreadStatus("closed")).toBe("closed");
  });

  it("falls back to active for unknown/future statuses", () => {
    expect(mapThreadStatus("some_new_status")).toBe("active");
  });
});

describe("formatShortDate", () => {
  it("formats an ISO date as a short human date", () => {
    expect(formatShortDate("2026-05-12T08:00:00Z")).toBe("May 12");
  });

  it("returns empty string for an unparseable date", () => {
    expect(formatShortDate("not-a-date")).toBe("");
  });
});

describe("toThreadSummary", () => {
  const base: ThreadV1 = {
    thread_id: "t-1",
    patient_id: "p-1",
    title: "Persistent cough",
    status: "active_unresolved",
    status_version: 1,
    schema_version: "c13.health_thread.v1",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-10T00:00:00Z",
  };

  it("maps a ThreadV1 onto the UI summary shape", () => {
    const s = toThreadSummary(base);
    expect(s.id).toBe("t-1");
    expect(s.title).toBe("Persistent cough");
    expect(s.status).toBe("active");
    expect(s.rawStatus).toBe("active_unresolved");
    expect(s.started).toBe("Started May 1");
    expect(s.updated).toBe("Updated May 10");
  });

  it("degrades gracefully when dates are unparseable", () => {
    const s = toThreadSummary({ ...base, created_at: "x", updated_at: "y" });
    expect(s.started).toBe("Started recently");
    expect(s.updated).toBe("Updated recently");
  });
});
