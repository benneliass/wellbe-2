/** In-process GraphStore. snapshot() is a JSON copy another lab can be built from. */

import {
  emptyDurableSnapshot,
  normalizeDurableSnapshot,
  type DurableSnapshot,
  type GraphStore,
} from "./graph-store.js";

export class MemoryGraphStore implements GraphStore {
  private current: DurableSnapshot = emptyDurableSnapshot();

  load(): DurableSnapshot {
    return normalizeDurableSnapshot(this.current);
  }

  save(snapshot: DurableSnapshot): void {
    this.current = normalizeDurableSnapshot(snapshot);
  }

  snapshot(): DurableSnapshot {
    return this.load();
  }

  replace(snapshot: DurableSnapshot): void {
    this.save(snapshot);
  }
}
