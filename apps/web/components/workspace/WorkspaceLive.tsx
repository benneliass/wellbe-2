"use client";

import { StateNote } from "@/components/placeholder/StateNote";
import { devSessionConfigured } from "@/lib/api";
import { usePendingItems, useThreads } from "@/lib/hooks";
import { WorkspaceHome } from "./WorkspaceHome";

/**
 * Fetches real threads (/v1/threads) and open loops (/v2/pending-items) and
 * renders the workspace, with calm loading / empty / error / sign-in states.
 * Replaces the previous mock-data render (Track 0.3, WEL-154).
 */
export function WorkspaceLive() {
  const threadsQuery = useThreads();
  const pendingQuery = usePendingItems();

  if (!devSessionConfigured && threadsQuery.isError) {
    return (
      <StateNote
        icon="lock"
        title="Sign in to see your workspace"
        description="Once you're signed in, your health threads and open loops appear here."
      />
    );
  }

  if (threadsQuery.isLoading) {
    return <StateNote icon="clock" title="Loading your workspace…" />;
  }

  if (threadsQuery.isError) {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your threads"
        description="Something went wrong reaching the server. Please try again in a moment."
      />
    );
  }

  const threads = threadsQuery.data ?? [];
  const pendingCount = pendingQuery.data?.length ?? 0;

  if (threads.length === 0) {
    return (
      <StateNote
        icon="folder"
        title="Nothing to carry forward yet"
        description="When you log something or a concern opens, it will show up here as a thread."
      />
    );
  }

  return <WorkspaceHome threads={threads} pendingCount={pendingCount} />;
}
