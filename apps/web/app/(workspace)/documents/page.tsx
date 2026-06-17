import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function DocumentsPage() {
  return (
    <>
      <TopBar title="Documents" breadcrumb="Documents" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="file-text"
          title="Your documents view is on the way"
          description="When this is ready, you'll find the reports, letters, and files you've added — each one linked to the thread and evidence it supports."
        />
      </PageBody>
    </>
  );
}
