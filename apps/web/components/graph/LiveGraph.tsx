"use client";

import { StateNote } from "@/components/placeholder/StateNote";
import { useLiveGraph } from "@/lib/graph-hooks";
import { GraphLive } from "./GraphLive";

/** The person's real graph in the cockpit, with calm loading / empty / error states. */
export function LiveGraph() {
  const state = useLiveGraph();

  if (state.status === "loading") {
    return <StateNote icon="git-fork" title="Mapping your records…" />;
  }
  if (state.status === "error") {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your graph"
        description="Your records are safe. Please try again in a moment."
      />
    );
  }
  if (state.status === "empty") {
    return (
      <StateNote
        icon="git-fork"
        title="Nothing to map yet"
        description="As you add symptoms, results, and notes, WellBe maps how they connect — traceable to the source, never a diagnosis."
      />
    );
  }
  return (
    <GraphLive
      model={state.model}
      notice={state.partial ? "Some details couldn't be loaded right now, so parts of the map may be missing." : undefined}
    />
  );
}
