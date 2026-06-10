import { notFound } from "next/navigation";
import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ThreadDetail } from "@/components/thread/ThreadDetail";
import { getThread } from "@/lib/mock-data";

export default async function ThreadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const thread = getThread(id);
  if (!thread) notFound();

  return (
    <>
      <TopBar
        title={thread.title}
        breadcrumb="Threads"
        subtitle={`${thread.started} · ${thread.updated}`}
        backHref="/workspace"
      />
      <PageBody>
        <ThreadDetail thread={thread} />
      </PageBody>
    </>
  );
}
