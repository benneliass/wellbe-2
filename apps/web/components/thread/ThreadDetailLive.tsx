"use client";

import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { StateNote } from "@/components/placeholder/StateNote";
import { ComingSoon } from "@/components/placeholder/ComingSoon";
import { formatShortDate, mapThreadStatus } from "@/lib/adapters";
import { STATUS_META } from "@/lib/meta";
import { useThread } from "@/lib/hooks";

/**
 * Live thread detail for real (non-demo) thread ids. The /v1/threads/{id} header
 * is honest about what's known today; the rich evidence/timeline view is wired in
 * a later track, so we show a calm "in progress" body rather than fabricating it.
 */
export function ThreadDetailLive({ id }: { id: string }) {
  const { data, isLoading, isError } = useThread(id);

  if (isLoading) {
    return (
      <>
        <TopBar title="Loading thread…" breadcrumb="Threads" backHref="/workspace" />
        <PageBody>
          <StateNote icon="clock" title="Loading this thread…" />
        </PageBody>
      </>
    );
  }

  if (isError || !data) {
    return (
      <>
        <TopBar title="Thread" breadcrumb="Threads" backHref="/workspace" />
        <PageBody>
          <StateNote
            icon="alert-circle"
            title="Couldn't load this thread"
            description="Something went wrong reaching the server. Please try again in a moment."
          />
        </PageBody>
      </>
    );
  }

  const status = STATUS_META[mapThreadStatus(data.status)];
  const started = formatShortDate(data.created_at);
  const updated = formatShortDate(data.updated_at);

  return (
    <>
      <TopBar
        title={data.title}
        breadcrumb="Threads"
        subtitle={[started && `Started ${started}`, updated && `Updated ${updated}`]
          .filter(Boolean)
          .join(" · ")}
        backHref="/workspace"
      />
      <PageBody>
        <ComingSoon
          icon={status.icon}
          title="The full thread view is on the way"
          description={`This is a real thread (status: ${status.label.toLowerCase()}). Its evidence, timeline, and open questions are being wired in — for now you can see its header above.`}
        />
      </PageBody>
    </>
  );
}
