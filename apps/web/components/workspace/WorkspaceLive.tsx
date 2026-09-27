"use client";

import { StateNote } from "@/components/placeholder/StateNote";
import { useSession } from "@/lib/useSession";
import { usePendingItems, useThreads } from "@/lib/hooks";
import { loopGroupOf } from "@/lib/home-continuity";
import { ThingsNoticed } from "./ThingsNoticed";
import { WhatChanged } from "./WhatChanged";
import { WorkspaceHome } from "./WorkspaceHome";

/**
 * Fetches real threads (/v1/threads) and open loops (/v2/pending-items) and
 * renders the workspace, with calm loading / empty / error / sign-in states.
 * Opens on what changed (WEL-145), then open loops, things noticed and threads.
 */
export function WorkspaceLive() {
  const signedIn = Boolean(useSession()?.patientId);
  const threadsQuery = useThreads();
  const pendingQuery = usePendingItems();

  if (!signedIn && threadsQuery.isError) {
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
  const loops = (pendingQuery.data ?? []).filter((p) => loopGroupOf(p.status) !== null);

  if (threads.length === 0) {
    return (
      <>
        <WhatChanged pending={loops} />
        <ThingsNoticed />
        <StateNote
          icon="folder"
          title="Nothing to carry forward yet"
          description="When you log something or a concern opens, it will show up here as a thread."
        />
      </>
    );
  }

  return (
    <>
      <WhatChanged pending={loops} />
      <WorkspaceHome
        threads={threads}
        pendingCount={loops.length}
        pendingItems={loops}
        afterLoops={<ThingsNoticed />}
      />
    </>
  );
}
