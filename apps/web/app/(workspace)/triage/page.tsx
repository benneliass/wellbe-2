import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function TriagePage() {
  return (
    <>
      <TopBar title="Something feels off" breadcrumb="Triage" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="heart-pulse"
          title="A calm check-in is on the way"
          description="When this is ready, you'll be able to describe what feels off and get steady, non-diagnostic guidance on what to watch and when to reach out — never an alarm, always your call."
        />
      </PageBody>
    </>
  );
}
