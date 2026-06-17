import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function ResultsPage() {
  return (
    <>
      <TopBar title="Results" breadcrumb="Results" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="flask-conical"
          title="Your results view is on the way"
          description="When this is ready, you'll see your labs and test results over time — what changed from your normal, what's still open, and which thread each one belongs to."
        />
      </PageBody>
    </>
  );
}
