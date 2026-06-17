import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function MemoryPage() {
  return (
    <>
      <TopBar title="Memory" breadcrumb="Memory" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="book"
          title="Your health memory is on the way"
          description="When this is ready, you'll see the story, clinical, pattern, decision, and responsibility memories WellBe keeps around each thread — your longitudinal record, source-linked and yours."
        />
      </PageBody>
    </>
  );
}
