import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { DeltaLive } from "@/components/delta/DeltaLive";

export default function DeltaPage() {
  return (
    <>
      <TopBar title="What changed?" breadcrumb="Delta Digest" backHref="/" />
      <PageBody>
        <DeltaLive />
      </PageBody>
    </>
  );
}
