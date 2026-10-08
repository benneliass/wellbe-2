import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { MemoryLive } from "@/components/records/MemoryLive";

export default async function MemoryPage({
  searchParams,
}: {
  searchParams: Promise<{ thread?: string | string[] }>;
}) {
  const { thread } = await searchParams;
  const threadId = Array.isArray(thread) ? thread[0] : thread;
  return (
    <>
      <TopBar title="Memory" breadcrumb="Memory" backHref="/" />
      <PageBody>
        <MemoryLive threadId={threadId || undefined} />
      </PageBody>
    </>
  );
}
