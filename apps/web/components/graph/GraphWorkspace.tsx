"use client";
import { useId, useState } from 'react';
import { Icon, Tabs } from '@wellbe/ui';
import { GraphLive, type GraphMode } from './GraphLive';
import { LiveGraph } from './LiveGraph';
import { ContextMap } from './ContextMap';
import type { GraphModel } from './graphData';
import styles from './GraphLive.module.css';

/** One workspace, two map policies. Keep each scene mounted to preserve its
 * camera, manual placements, filters and path when changing the visible map. */
export function GraphWorkspace({ model, preview = false, initialContext = false }: { model?: GraphModel; preview?: boolean; initialContext?: boolean }) {
  const [graphOpened, setGraphOpened] = useState(!initialContext);
  const [mode, setMode] = useState<GraphMode>('detail');
  const [context, setContext] = useState(initialContext);
  const [contextOpened, setContextOpened] = useState(initialContext);
  const panel = useId();
  const navigation = <div className={styles.mapModes} aria-label="Map purpose">
    <Tabs items={[
      { id: 'overview', label: 'Overview' },
      { id: 'detail', label: 'Cluster detail' },
      { id: 'explore', label: 'Explore all' },
      { id: 'context', label: 'Context map', variant: 'distinct', icon: <Icon name="file-text" size={14} /> },
    ]} value={context ? 'context' : mode} onChange={(id) => {
      if (id === 'context') { setContextOpened(true); setContext(true); }
      else { setMode(id as GraphMode); setGraphOpened(true); setContext(false); }
    }} />
  </div>;
  return <div className={styles.mapWorkspace}>
    <div className={context ? styles.inactiveMap : undefined} aria-hidden={context || undefined} inert={context || undefined}>
      {graphOpened && (model ? <GraphLive model={model} viewMode={mode} onViewModeChange={setMode} modeNavigation={navigation} /> : <LiveGraph viewMode={mode} onViewModeChange={setMode} modeNavigation={navigation} />)}
    </div>
    {contextOpened && <div id={`${panel}-context`} className={!context ? styles.inactiveMap : undefined} aria-hidden={!context || undefined} inert={!context || undefined}>
      <div className={styles.toolbar}>{context && navigation}</div>
      <ContextMap preview={preview} embedded />
    </div>}
  </div>;
}
