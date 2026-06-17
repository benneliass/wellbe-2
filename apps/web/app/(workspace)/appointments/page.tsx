import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function AppointmentsPage() {
  return (
    <>
      <TopBar title="Appointments" breadcrumb="Appointments" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="calendar"
          title="Your appointments view is on the way"
          description="When this is ready, you'll see past and upcoming visits, what each one was for, and the open loops to follow up on — so nothing falls through between appointments."
        />
      </PageBody>
    </>
  );
}
