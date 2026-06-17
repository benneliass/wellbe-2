import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { WorkspaceLive } from "@/components/workspace/WorkspaceLive";

export default function WorkspacePage() {
  return (
    <>
      <TopBar
        title="Carrying forward"
        subtitle="What concerns am I holding, and what changed from my normal?"
      />
      <PageBody>
        <WorkspaceLive />
      </PageBody>
    </>
  );
}
