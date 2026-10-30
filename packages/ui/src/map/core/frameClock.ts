type Listener = { paint: (now: number) => void; order: number };
type Scheduler = { request: (paint: FrameRequestCallback) => number; cancel: (id: number) => void };

/** One animation frame per mounted scene, independent of its number of objects
 * or links. The scheduler is injectable for deterministic lifecycle tests.
 */
export class MapFrameClock {
  private listeners = new Set<Listener>();
  private frame: number | null = null;
  constructor(private scheduler: Scheduler, private onError: (error: unknown) => void = (error) => { queueMicrotask(() => { throw error; }); }) {}
  subscribe(paint: (now: number) => void, order = 0): () => void {
    const listener = { paint, order };
    this.listeners.add(listener);
    this.schedule();
    return () => {
      this.listeners.delete(listener);
      if (!this.listeners.size && this.frame !== null) { this.scheduler.cancel(this.frame); this.frame = null; }
    };
  }
  private schedule() {
    if (this.frame === null && this.listeners.size) this.frame = this.scheduler.request(this.tick);
  }
  private tick = (now: number) => {
    this.frame = null;
    for (const listener of [...this.listeners].sort((a, b) => a.order - b.order)) if (this.listeners.has(listener)) {
      try { listener.paint(now); } catch (error) { this.onError(error); }
    }
    this.schedule();
  };
}

const clocks = new WeakMap<SVGSVGElement, MapFrameClock>();
export function subscribeMapFrame(scene: SVGSVGElement, paint: (now: number) => void, order = 0) {
  let clock = clocks.get(scene);
  if (!clock) {
    clock = new MapFrameClock({ request: (tick) => requestAnimationFrame(tick), cancel: (id) => cancelAnimationFrame(id) });
    clocks.set(scene, clock);
  }
  return clock.subscribe(paint, order);
}
