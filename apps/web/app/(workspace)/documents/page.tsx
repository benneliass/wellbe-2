import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { DocumentsLive } from "@/components/documents/DocumentsLive";

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{ file?: string | string[] }>;
}) {
  const { file } = await searchParams;
  const fileName = Array.isArray(file) ? file[0] : file;
  return (
    <>
      <TopBar title="Documents" breadcrumb="Documents" backHref="/" />
      <PageBody>
        <DocumentsLive fileName={fileName || undefined} />
      </PageBody>
    </>
  );
}
