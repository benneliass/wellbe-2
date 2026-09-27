import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { GraphLive } from "@/components/graph/GraphLive";
import { PersonGraph } from "@/components/graph/PersonGraph";

export default async function GraphPage({
  searchParams,
}: {
  searchParams: Promise<{ preview?: string }>;
}) {
  // The full-vision interaction prototype runs on sample fixtures, so it is only
  // reachable as an explicitly labelled design preview — never as the person's graph.
  const { preview } = await searchParams;
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
      <PageBody>{designPreview ? <GraphLive /> : <PersonGraph />}</PageBody>
    </>
  );
}
