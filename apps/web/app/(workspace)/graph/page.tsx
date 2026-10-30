import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { GraphWorkspace } from "@/components/graph/GraphWorkspace";
import { DESIGN_PREVIEW_MODEL } from "@/components/graph/graphData";

export default async function GraphPage({
  searchParams,
}: {
  searchParams: Promise<{ preview?: string; view?: string }>;
}) {
  // The sample-fixture cockpit is only reachable as an explicitly labelled design
  // preview — never as the person's graph.
  const { preview, view } = await searchParams;
  const designPreview = preview === "design";

  return (
    <>
      <TopBar
        title="Open the graph"
        subtitle={
          designPreview
            ? "Design preview with sample data — not your records."
            : "A whole-person map of how your concerns, events, and evidence connect — scoped to you, traceable to its sources, never a diagnosis."
        }
        breadcrumb="Deep Dive"
        backHref="/"
      />
      <PageBody>{designPreview ? <GraphWorkspace preview initialContext={view === "context"} model={{ ...DESIGN_PREVIEW_MODEL, autoLayout: true }} /> : <GraphWorkspace initialContext={view === "context"} />}</PageBody>
    </>
  );
}
