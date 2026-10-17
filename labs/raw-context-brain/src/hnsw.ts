import { cosineDistance, mulberry32 } from "./text.js";

interface HnswNode {
  id: string;
  vector: Float64Array;
  level: number;
  links: string[][];
}

/**
 * Small deterministic HNSW used only to seed candidates.
 * Approximate misses are not evidence that related context is absent.
 */
export class HnswIndex {
  readonly dim: number;
  searchCount = 0;
  private readonly nodes = new Map<string, HnswNode>();
  private readonly rng: () => number;
  private entryId: string | null = null;
  private maxLevel = 0;
  private readonly m: number;
  private readonly m0: number;
  private readonly efConstruction: number;
  private readonly ml: number;

  constructor(seed = 1, dim = 32) {
    this.dim = dim;
    this.rng = mulberry32(seed);
    this.m = 8;
    this.m0 = 16;
    this.efConstruction = 32;
    this.ml = 1 / Math.log(2);
  }

  get size(): number {
    return this.nodes.size;
  }

  add(id: string, vector: Float64Array): void {
    if (this.nodes.has(id)) return;
    const level = this.randomLevel();
    const node: HnswNode = { id, vector, level, links: [] };
    for (let layer = 0; layer <= level; layer += 1) node.links[layer] = [];
    this.nodes.set(id, node);
    if (this.entryId === null) {
      this.entryId = id;
      this.maxLevel = level;
      return;
    }

    let enter = this.entryId;
    for (let layer = this.maxLevel; layer > level; layer -= 1) {
      const nearest = this.searchLayer(vector, enter, 1, layer);
      if (nearest[0]) enter = nearest[0].id;
    }
    const limit = Math.min(level, this.maxLevel);
    for (let layer = limit; layer >= 0; layer -= 1) {
      const neighbors = this.searchLayer(vector, enter, this.efConstruction, layer);
      const selected = neighbors.slice(0, this.maxFor(layer));
      for (const neighbor of selected) {
        this.connect(id, neighbor.id, layer);
        this.prune(neighbor.id, layer);
      }
      if (neighbors[0]) enter = neighbors[0].id;
    }
    if (level > this.maxLevel) {
      this.maxLevel = level;
      this.entryId = id;
    }
  }

  search(vector: Float64Array, k: number, ef = 32): Array<{ id: string; distance: number }> {
    this.searchCount += 1;
    if (!this.entryId) return [];
    let enter = this.entryId;
    for (let layer = this.maxLevel; layer > 0; layer -= 1) {
      const nearest = this.searchLayer(vector, enter, 1, layer);
      if (nearest[0]) enter = nearest[0].id;
    }
    return this.searchLayer(vector, enter, Math.max(k, ef), 0).slice(0, k);
  }

  /** Exact scan of stored vectors. Used to measure approximate recall, not as source truth. */
  bruteForce(vector: Float64Array, k: number, exclude?: string): Array<{ id: string; distance: number }> {
    const scored: Array<{ id: string; distance: number }> = [];
    for (const node of this.nodes.values()) {
      if (node.id === exclude) continue;
      scored.push({ id: node.id, distance: cosineDistance(vector, node.vector) });
    }
    scored.sort((a, b) => a.distance - b.distance || (a.id < b.id ? -1 : 1));
    return scored.slice(0, k);
  }

  private randomLevel(): number {
    return Math.floor(-Math.log(Math.max(this.rng(), 1e-12)) * this.ml);
  }

  private maxFor(layer: number): number {
    return layer === 0 ? this.m0 : this.m;
  }

  private connect(a: string, b: string, layer: number): void {
    if (a === b) return;
    const left = this.nodes.get(a);
    const right = this.nodes.get(b);
    if (!left || !right) return;
    if (left.level < layer || right.level < layer) return;
    if (!left.links[layer]) left.links[layer] = [];
    if (!right.links[layer]) right.links[layer] = [];
    if (!left.links[layer].includes(b)) left.links[layer].push(b);
    if (!right.links[layer].includes(a)) right.links[layer].push(a);
  }

  private prune(id: string, layer: number): void {
    const node = this.nodes.get(id);
    if (!node) return;
    const links = node.links[layer] ?? [];
    const cap = this.maxFor(layer);
    if (links.length <= cap) return;
    const ranked = links
      .map((other) => ({
        id: other,
        distance: cosineDistance(node.vector, this.nodes.get(other)!.vector),
      }))
      .sort((a, b) => a.distance - b.distance || (a.id < b.id ? -1 : 1));
    const keep = new Set(ranked.slice(0, cap).map((item) => item.id));
    node.links[layer] = links.filter((other) => keep.has(other));
    for (const other of links) {
      if (keep.has(other)) continue;
      const neighbor = this.nodes.get(other);
      if (!neighbor?.links[layer]) continue;
      neighbor.links[layer] = neighbor.links[layer].filter((link) => link !== id);
    }
  }

  private searchLayer(
    vector: Float64Array,
    entryId: string,
    ef: number,
    layer: number,
  ): Array<{ id: string; distance: number }> {
    const entry = this.nodes.get(entryId);
    if (!entry) return [];
    const visited = new Set<string>([entryId]);
    const candidates: Array<{ id: string; distance: number }> = [
      { id: entryId, distance: cosineDistance(vector, entry.vector) },
    ];
    const best: Array<{ id: string; distance: number }> = [...candidates];

    while (candidates.length > 0) {
      candidates.sort((a, b) => a.distance - b.distance || (a.id < b.id ? -1 : 1));
      const current = candidates.shift();
      if (!current) break;
      best.sort((a, b) => b.distance - a.distance || (a.id < b.id ? -1 : 1));
      const worst = best[0];
      if (best.length >= ef && worst && current.distance > worst.distance) break;
      const node = this.nodes.get(current.id);
      for (const neighborId of node?.links[layer] ?? []) {
        if (visited.has(neighborId)) continue;
        visited.add(neighborId);
        const neighbor = this.nodes.get(neighborId);
        if (!neighbor) continue;
        const distance = cosineDistance(vector, neighbor.vector);
        const furthest = best[0];
        if (best.length < ef || (furthest && distance < furthest.distance)) {
          candidates.push({ id: neighborId, distance });
          best.push({ id: neighborId, distance });
          best.sort((a, b) => b.distance - a.distance || (a.id < b.id ? -1 : 1));
          if (best.length > ef) best.shift();
        }
      }
    }
    best.sort((a, b) => a.distance - b.distance || (a.id < b.id ? -1 : 1));
    return best;
  }
}
