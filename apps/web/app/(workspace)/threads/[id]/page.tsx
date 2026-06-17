import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ThreadDetail } from "@/components/thread/ThreadDetail";
import { ThreadDetailLive } from "@/components/thread/ThreadDetailLive";
import { getThread } from "@/lib/mock-data";

export default async function ThreadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const thread = getThread(id);

  // Demo ids keep the rich curated view; any other id is a real thread fetched
  // live from /v1/threads/{id} (Track 0.3, WEL-154).
  if (!thread) return <ThreadDetailLive id={id} />;

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
