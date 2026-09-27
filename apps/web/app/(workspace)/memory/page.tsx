import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { MemoryLive } from "@/components/records/MemoryLive";

export default function MemoryPage() {
  return (
    <>
      <TopBar title="Memory" breadcrumb="Memory" backHref="/" />
      <PageBody>
        <MemoryLive />
      </PageBody>
    </>
  );
}
