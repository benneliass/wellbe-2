import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { PatternsLive } from "@/components/patterns/PatternsLive";

export default function PatternsPage() {
  return (
    <>
      <TopBar title="Check my patterns" breadcrumb="Pattern Check" backHref="/" />
      <PageBody>
        <PatternsLive />
      </PageBody>
    </>
  );
}
