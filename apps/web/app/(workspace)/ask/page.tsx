import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

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
        <ComingSoon
          icon="message-circle"
          title="Ask WellBe is being built"
          description="Soon you'll be able to ask about your own health in plain language and get a calm, source-linked answer — never a diagnosis, always grounded in your data."
          echo={query ? `You asked: “${query}”` : undefined}
        />
      </PageBody>
    </>
  );
}
