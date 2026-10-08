import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ResultsLive } from "@/components/results/ResultsLive";

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ document?: string | string[]; analyte?: string | string[] }>;
}) {
  const { document, analyte } = await searchParams;
  const documentId = Array.isArray(document) ? document[0] : document;
  const analyteName = Array.isArray(analyte) ? analyte[0] : analyte;
  return (
    <>
      <TopBar title="Results" breadcrumb="Results" backHref="/" />
      <PageBody>
        <ResultsLive documentId={documentId || undefined} analyteName={analyteName || undefined} />
      </PageBody>
    </>
  );
}
