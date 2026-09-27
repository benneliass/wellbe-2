import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { DocumentsLive } from "@/components/documents/DocumentsLive";

export default function DocumentsPage() {
  return (
    <>
      <TopBar title="Documents" breadcrumb="Documents" backHref="/" />
      <PageBody>
        <DocumentsLive />
      </PageBody>
    </>
  );
}
