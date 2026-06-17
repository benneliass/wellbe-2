import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { AskLive } from "@/components/ask/AskLive";

export default async function AskPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = typeof q === "string" ? q.trim() : "";

  return (
    <>
      <TopBar title="Ask WellBe" breadcrumb="Ask" backHref="/" />
      <PageBody>
        <AskLive initialQuery={query} />
      </PageBody>
    </>
  );
}
