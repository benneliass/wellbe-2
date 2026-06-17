import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { PrepareLive } from "@/components/prepare/PrepareLive";

export default function PreparePage() {
  return (
    <>
      <TopBar title="Prepare for appointment" breadcrumb="Doctor Prep" backHref="/" />
      <PageBody>
        <PrepareLive />
      </PageBody>
    </>
  );
}
