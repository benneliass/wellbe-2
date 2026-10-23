"""Small deterministic HNSW used only to seed candidates.

Approximate misses are not evidence that related context is absent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from wellbe_raw_context_brain.text import cosine_distance, mulberry32


@dataclass
class _Node:
    id: str
    vector: list[float]
    level: int
    links: list[list[str]]


@dataclass(frozen=True)
class HnswHit:
    id: str
    distance: float


def _by_distance(hit: HnswHit) -> tuple[float, str]:
    return (hit.distance, hit.id)


def _by_distance_desc(hit: HnswHit) -> tuple[float, str]:
    return (-hit.distance, hit.id)


class HnswIndex:
    def __init__(self, seed: int = 1, dim: int = 32) -> None:
        self.dim = dim
        self.search_count = 0
        self._nodes: dict[str, _Node] = {}
        self._rng = mulberry32(seed)
        self._entry_id: str | None = None
        self._max_level = 0
        self._m = 8
        self._m0 = 16
        self._ef_construction = 32
        self._ml = 1 / math.log(2)

    @property
    def size(self) -> int:
        return len(self._nodes)

    def add(self, node_id: str, vector: list[float]) -> None:
        if node_id in self._nodes:
            return
        level = self._random_level()
        node = _Node(id=node_id, vector=vector, level=level, links=[[] for _ in range(level + 1)])
        self._nodes[node_id] = node
        if self._entry_id is None:
            self._entry_id = node_id
            self._max_level = level
            return

        enter = self._entry_id
        for layer in range(self._max_level, level, -1):
            nearest = self._search_layer(vector, enter, 1, layer)
            if nearest:
                enter = nearest[0].id
        limit = min(level, self._max_level)
        for layer in range(limit, -1, -1):
            neighbors = self._search_layer(vector, enter, self._ef_construction, layer)
            selected = neighbors[: self._max_for(layer)]
            for neighbor in selected:
                self._connect(node_id, neighbor.id, layer)
                self._prune(neighbor.id, layer)
            if neighbors:
                enter = neighbors[0].id
        if level > self._max_level:
            self._max_level = level
            self._entry_id = node_id

    def search(self, vector: list[float], k: int, ef: int = 32) -> list[HnswHit]:
        self.search_count += 1
        if self._entry_id is None:
            return []
        enter = self._entry_id
        for layer in range(self._max_level, 0, -1):
            nearest = self._search_layer(vector, enter, 1, layer)
            if nearest:
                enter = nearest[0].id
        return self._search_layer(vector, enter, max(k, ef), 0)[:k]

    def brute_force(self, vector: list[float], k: int, exclude: str | None = None) -> list[HnswHit]:
        """Exact scan of stored vectors. Measures approximate recall, not source truth."""
        scored: list[HnswHit] = []
        for node in self._nodes.values():
            if node.id == exclude:
                continue
            scored.append(HnswHit(id=node.id, distance=cosine_distance(vector, node.vector)))
        scored.sort(key=_by_distance)
        return scored[:k]

    def _random_level(self) -> int:
        return math.floor(-math.log(max(self._rng(), 1e-12)) * self._ml)

    def _max_for(self, layer: int) -> int:
        if layer == 0:
            return self._m0
        return self._m

    def _connect(self, left_id: str, right_id: str, layer: int) -> None:
        if left_id == right_id:
            return
        left = self._nodes.get(left_id)
        right = self._nodes.get(right_id)
        if left is None or right is None:
            return
        if left.level < layer or right.level < layer:
            return
        while len(left.links) <= layer:
            left.links.append([])
        while len(right.links) <= layer:
            right.links.append([])
        if right_id not in left.links[layer]:
            left.links[layer].append(right_id)
        if left_id not in right.links[layer]:
            right.links[layer].append(left_id)

    def _prune(self, node_id: str, layer: int) -> None:
        node = self._nodes.get(node_id)
        if node is None:
            return
        links = node.links[layer] if layer < len(node.links) else []
        cap = self._max_for(layer)
        if len(links) <= cap:
            return
        ranked = [
            HnswHit(
                id=other,
                distance=cosine_distance(node.vector, self._nodes[other].vector),
            )
            for other in links
        ]
        ranked.sort(key=_by_distance)
        keep = {item.id for item in ranked[:cap]}
        node.links[layer] = [other for other in links if other in keep]
        for other in links:
            if other in keep:
                continue
            neighbor = self._nodes.get(other)
            if neighbor is None or layer >= len(neighbor.links):
                continue
            neighbor.links[layer] = [link for link in neighbor.links[layer] if link != node_id]

    def _search_layer(
        self,
        vector: list[float],
        entry_id: str,
        ef: int,
        layer: int,
    ) -> list[HnswHit]:
        entry = self._nodes.get(entry_id)
        if entry is None:
            return []
        visited = {entry_id}
        candidates = [HnswHit(id=entry_id, distance=cosine_distance(vector, entry.vector))]
        best = list(candidates)
        while candidates:
            candidates.sort(key=_by_distance)
            current = candidates.pop(0)
            best.sort(key=_by_distance_desc)
            worst = best[0]
            if len(best) >= ef and current.distance > worst.distance:
                break
            node = self._nodes.get(current.id)
            neighbor_ids = node.links[layer] if node is not None and layer < len(node.links) else []
            for neighbor_id in neighbor_ids:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                neighbor = self._nodes.get(neighbor_id)
                if neighbor is None:
                    continue
                distance = cosine_distance(vector, neighbor.vector)
                furthest = best[0]
                if len(best) < ef or distance < furthest.distance:
                    candidates.append(HnswHit(id=neighbor_id, distance=distance))
                    best.append(HnswHit(id=neighbor_id, distance=distance))
                    best.sort(key=_by_distance_desc)
                    if len(best) > ef:
                        best.pop(0)
        best.sort(key=_by_distance)
        return best
