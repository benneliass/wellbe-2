import { PageBody } from "@/components/shell/AppShell";
import { TopBar } from "@/components/shell/TopBar";
import { ComingSoon } from "@/components/placeholder/ComingSoon";

export default function PatternsPage() {
  return (
    <>
      <TopBar title="Check my patterns" breadcrumb="Pattern Check" backHref="/" />
      <PageBody>
        <ComingSoon
          icon="bar-chart-3"
          title="Pattern check is being built"
          description="Soon this will surface connections across your own health over time — never a diagnosis, always source-linked so you can see exactly where each observation comes from."
        />
      </PageBody>
    </>
  );
}
