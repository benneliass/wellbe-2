import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function DeltaPage() {
  return (
    <>
      <TopBar title="What changed?" breadcrumb="Delta Digest" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="activity"
          title="Your what-changed digest is being built"
          description="Soon this will gather what's new across your notes, results, and documents since you last looked — so nothing meaningful slips by unseen."
        />
      </PageBody>
    </>
  );
}
