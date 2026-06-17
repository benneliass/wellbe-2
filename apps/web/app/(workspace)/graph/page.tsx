import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function GraphPage() {
  return (
    <>
      <TopBar title="Open the graph" breadcrumb="Deep Dive" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="git-fork"
          title="Your health graph is being built"
          description="Soon you'll be able to explore how your threads, events, and evidence connect — a visual map of your own health, scoped to you and traceable to its sources."
        />
      </PageBody>
    </>
  );
}
