import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { OpenLoopsLive } from "@/components/records/OpenLoopsLive";

export default function AppointmentsPage() {
  return (
    <>
      <TopBar title="Appointments" breadcrumb="Appointments" backHref="/" />
      <PageBody>
        <OpenLoopsLive />
      </PageBody>
    </>
  );
}
