import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationBell } from "./NotificationBell";

const markRead = vi.fn();
const markAll = vi.fn();
let list: { notifications: Record<string, unknown>[]; unread_count: number } = {
  notifications: [],
  unread_count: 0,
};

vi.mock("@/lib/useSession", () => ({ useSession: () => ({ patientId: "p" }) }));
vi.mock("@/lib/hooks", () => ({
  useNotifications: () => ({ data: list, isError: false }),
  useMarkNotificationRead: () => ({ mutate: markRead, isPending: false }),
  useMarkAllNotificationsRead: () => ({ mutate: markAll, isPending: false }),
}));

function notification(over: Record<string, unknown>) {
  return {
    schema_version: "c13.notification.v2",
    notification_id: "n1",
    kind: "pending_item_due",
    title: "A follow-up is due: Waiting for a result: Ferritin",
    body: "If the result has come in, you can add it to the thread.",
    pending_item_id: "pi1",
    thread_id: "t1",
    created_at: "2026-09-27T10:00:00Z",
    read_at: null,
    ...over,
  };
}

describe("NotificationBell", () => {
  beforeEach(() => {
    markRead.mockReset();
    markAll.mockReset();
    list = { notifications: [], unread_count: 0 };
  });

  it("shows a calm empty state", () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));
    expect(screen.getByText(/caught up/i)).toBeInTheDocument();
  });

  it("badges the unread count and lists reminders linking to their thread", () => {
    list = {
      notifications: [notification({}), notification({ notification_id: "n2", read_at: "x" })],
      unread_count: 1,
    };
    render(<NotificationBell />);
    const bell = screen.getByRole("button", { name: /notifications, 1 unread/i });
    expect(bell).toHaveTextContent("1");
    fireEvent.click(bell);
    const [link] = screen.getAllByRole("link", { name: /a follow-up is due/i });
    if (!link) throw new Error("no reminder link");
    expect(link).toHaveAttribute("href", "/threads/t1");
    fireEvent.click(link);
    expect(markRead).toHaveBeenCalledWith("n1");
  });

  it("marks one or all as read", () => {
    list = { notifications: [notification({})], unread_count: 1 };
    render(<NotificationBell />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));
    fireEvent.click(screen.getByRole("button", { name: /mark ".*" as read/i }));
    expect(markRead).toHaveBeenCalledWith("n1");
    fireEvent.click(screen.getByRole("button", { name: /mark all read/i }));
    expect(markAll).toHaveBeenCalled();
  });
});
