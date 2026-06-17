import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function PreparePage() {
  return (
    <>
      <TopBar title="Prepare for appointment" breadcrumb="Doctor Prep" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="user"
          title="Appointment prep is being built"
          description="Soon you'll be able to build a source-linked packet for an upcoming visit — what to raise, what's still open, what's changed — and choose exactly what to share, on your terms."
        />
      </PageBody>
    </>
  );
}
