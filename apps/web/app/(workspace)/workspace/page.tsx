import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { WorkspaceHome } from "@/components/workspace/WorkspaceHome";
import { getThreads } from "@/lib/mock-data";

export default function WorkspacePage() {
  const threads = getThreads();
  return (
    <>
      <TopBar
        title="Carrying forward"
        subtitle="What concerns am I holding, and what changed from my normal?"
      />
      <PageBody>
        <WorkspaceHome threads={threads} />
      </PageBody>
    </>
  );
}
