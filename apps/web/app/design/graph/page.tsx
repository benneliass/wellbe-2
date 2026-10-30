import { Wordmark } from "@wellbe/ui";
import { GraphWorkspace } from "@/components/graph/GraphWorkspace";
import { DESIGN_PREVIEW_MODEL } from "@/components/graph/graphData";
import mapStyles from "@/components/graph/ContextMap.module.css";
import styles from "../preview.module.css";

export default async function GraphDesignPage({ searchParams }: { searchParams: Promise<{ view?: string }> }) {
  const { view } = await searchParams;
  return <>
    <header className={`${mapStyles.header} ${styles.graphHeader}`}>
      <div className={mapStyles.titleRow}>
        <Wordmark size={24} />
        <nav className={mapStyles.tabs} aria-label="Record views">
          <h1 aria-current="page">Graph</h1>
        </nav>
      </div>
      <span className={mapStyles.preview}>Design preview · Sample records, not your data</span>
    </header>
    <GraphWorkspace preview initialContext={view === "context"} model={{ ...DESIGN_PREVIEW_MODEL, autoLayout: true }} />
  </>;
}
