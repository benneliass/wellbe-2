"""Synthetic maps for the lab.

Display metadata uses no extra draws, so the link pattern stays put.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.text import mulberry32, sha256
from wellbe_raw_context_brain.types import Independence, SourceArrival, VaultEvent

TopologyKind = Literal["sparse", "dense", "cyclic", "hub", "varied"]

_MOTIFS = ("sleep", "glucose", "knee", "headache", "travel")
_SOURCE_TYPES = ("note", "lab_text", "image_caption", "pdf_extract")


def _arrival(
    index: int,
    source_type: str,
) -> tuple[Independence, SourceArrival, str | None]:
    if source_type in {"pdf_extract", "image_caption"}:
        return ("source_family", "imported", None)
    if index > 0 and index % 7 == 0:
        return ("unknown", "copied", f"n{index - 1}")
    return ("source_family", "typed", None)


def _captured_at(index: int) -> str:
    moment = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def generate_topology(
    *,
    count: int,
    kind: TopologyKind,
    seed: int = 1,
    person_id: str = "synthetic-1",
    page_size: int | None = None,
    hop_limit: int | None = None,
    expansion_budget: int | None = None,
) -> RawContextLab:
    random = mulberry32(seed)
    options = LabOptions(seed=seed)
    if page_size is not None:
        options.page_size = page_size
    if hop_limit is not None:
        options.hop_limit = hop_limit
    if expansion_budget is not None:
        options.expansion_budget = expansion_budget
    lab = RawContextLab(options)

    for index in range(count):
        motif = _MOTIFS[index % len(_MOTIFS)]
        source_type = _SOURCE_TYPES[index % len(_SOURCE_TYPES)]
        independence, arrival, copied_from_id = _arrival(index, source_type)
        document_id = f"doc-{index // 11}" if index % 11 == 0 else None
        if kind == "varied":
            document_id = None
        text = f"{motif} note {index} sample {math.floor(random() * 1000)}"
        lab.add_fixture(
            VaultEvent(
                id=f"n{index}",
                person_id=person_id,
                captured_at=_captured_at(index),
                source_type=source_type,
                text=text,
                content_hash=sha256(text),
                lineage_id=f"{motif}-{index // 5}",
                document_id=document_id,
                independence=independence,
                source_arrival=arrival,
                copied_from_id=copied_from_id,
            )
        )

    def link(left: int, right: int) -> None:
        if right < 0 or right >= count or left == right:
            return
        lab.link_structural(f"n{left}", f"n{right}", "recorded_association")

    if kind == "hub":
        for index in range(1, count):
            link(0, index)
        return lab

    if kind == "varied":
        _varied_links(count, random, link)
        return lab

    for index in range(1, count):
        if kind == "sparse" and index % 17 == 0:
            continue
        link(index - 1, index)
        if kind == "dense":
            link(index, index + 1)
            link(index, index + 2)
        if kind == "cyclic" and index % 5 == 0:
            link(index, index - 3)
    return lab


def _varied_links(
    count: int,
    draw: Callable[[], float],
    connect_link: Callable[[int, int], None],
) -> None:
    neighbors: list[set[int]] = [set() for _ in range(count)]

    def connect(left: int, right: int) -> bool:
        if left == right or left < 0 or right < 0 or left >= count or right >= count:
            return False
        if right in neighbors[left]:
            return False
        neighbors[left].add(right)
        neighbors[right].add(left)
        return True

    target = [0] * count
    for index in range(count):
        roll = draw()
        if roll < 0.16:
            target[index] = 0
        elif roll < 0.42:
            target[index] = 1
        elif roll < 0.74:
            target[index] = 2 + math.floor(draw() * 3)
        elif roll < 0.92:
            target[index] = 6 + math.floor(draw() * 7)
        else:
            target[index] = 14 + math.floor(draw() * 10)
    stubs: list[int] = []
    for index, degree in enumerate(target):
        stubs.extend([index] * degree)
    _shuffle(stubs, draw)
    if len(stubs) % 2 == 1:
        stubs.pop()
    for index in range(0, len(stubs), 2):
        connect(stubs[index], stubs[index + 1])
    hub_count = max(3, min(8, math.floor(count / 40 + 0.5)))
    hubs = sorted(range(count), key=lambda index: len(neighbors[index]), reverse=True)[:hub_count]
    for hub in hubs:
        goal = 30 + math.floor(draw() * 21)
        others = list(range(count))
        _shuffle(others, draw)
        for other in others:
            if len(neighbors[hub]) >= goal:
                break
            connect(hub, other)
    for left in range(count):
        for right in neighbors[left]:
            if left < right:
                connect_link(left, right)


def _shuffle(items: list[int], draw: Callable[[], float]) -> None:
    for index in range(len(items) - 1, 0, -1):
        swap = math.floor(draw() * (index + 1))
        current = items[index]
        items[index] = items[swap]
        items[swap] = current
