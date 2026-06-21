import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { GraphLive } from "@/components/graph/GraphLive";

export default function GraphPage() {
  return (
    <>
      <TopBar
        title="Open the graph"
        subtitle="A whole-person map of how your concerns, events, and evidence connect — scoped to you, traceable to its sources, never a diagnosis."
        breadcrumb="Deep Dive"
        backHref="/"
      />
      <PageBody>
        <GraphLive />
      </PageBody>
    </>
  );
}
