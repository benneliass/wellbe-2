import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { TriageCheckIn } from "@/components/triage/TriageCheckIn";

export default function TriagePage() {
  return (
    <>
      <TopBar title="A calm check-in" breadcrumb="Check-in" backHref="/" />
      <PageBody>
        <TriageCheckIn />
      </PageBody>
    </>
  );
}
