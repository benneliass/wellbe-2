#!/usr/bin/env python3
"""Inspect and repair the transactional outbox (events.outbox_events).

Consumers retry failed events with backoff and dead-letter them after
WELLBE_OUTBOX_MAX_ATTEMPTS failures (see wellbe_events.retry). This script shows
the backlog and puts dead-lettered events back in the queue once the cause is
fixed.

Requires asyncpg, which the backend workspace provides. Reads DATABASE_URL
(falls back to WELLBE_DATABASE_URL); SQLAlchemy-style URLs such as
``postgresql+asyncpg://...`` are accepted. Run from the repo root:

    export DATABASE_URL=postgresql://wellbe:wellbe_dev@localhost:5432/wellbe
    uv run --project backend python scripts/ops/outbox.py stats
    uv run --project backend python scripts/ops/outbox.py dead [--event-type T] [--limit N] [--full]
    uv run --project backend python scripts/ops/outbox.py requeue <id> [<id> ...]
    uv run --project backend python scripts/ops/outbox.py requeue --all-dead [--event-type T]

Commands:
  stats    Per event_type counts of undelivered rows: pending (never failed),
           retrying (failed, backing off), dead (dead-lettered), and the age of
           the oldest live row.
  dead     List dead-lettered rows with attempts and last_error (first line,
           truncated; --full prints the whole stored error).
  requeue  Reset attempts/last_error and clear dead_lettered_at/next_attempt_at
           so consumers pick the rows up on their next poll. Accepts explicit ids
           (dead or still backing off) or --all-dead. Delivered rows are never
           touched.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import uuid
from typing import Any

STATS_SQL = """
SELECT event_type,
       count(*) FILTER (WHERE dead_lettered_at IS NULL AND last_error IS NULL) AS pending,
       count(*) FILTER (WHERE dead_lettered_at IS NULL AND last_error IS NOT NULL) AS retrying,
       count(*) FILTER (WHERE dead_lettered_at IS NOT NULL) AS dead,
       extract(epoch FROM now() - min(created_at) FILTER (WHERE dead_lettered_at IS NULL))
           AS oldest_live_s
FROM events.outbox_events
WHERE delivered_at IS NULL
GROUP BY event_type
ORDER BY event_type
"""

DEAD_SQL = """
SELECT id, event_type, attempts, created_at, dead_lettered_at, last_error
FROM events.outbox_events
WHERE delivered_at IS NULL AND dead_lettered_at IS NOT NULL
  AND ($1::text IS NULL OR event_type = $1)
ORDER BY dead_lettered_at
LIMIT $2
"""

_RESET = """
UPDATE events.outbox_events
SET attempts = 0, last_error = NULL, next_attempt_at = NULL, dead_lettered_at = NULL
WHERE delivered_at IS NULL AND {where}
RETURNING id
"""
REQUEUE_IDS_SQL = _RESET.format(where="id = ANY($1::uuid[])")
REQUEUE_DEAD_SQL = _RESET.format(
    where="dead_lettered_at IS NOT NULL AND ($1::text IS NULL OR event_type = $1)"
)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("WELLBE_DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set")
    return re.sub(r"^postgres(ql)?\+\w+://", "postgresql://", url)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))]
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) for r in rows]
    return "\n".join(lines)


async def cmd_stats(conn: Any, args: argparse.Namespace) -> int:
    rows = await conn.fetch(STATS_SQL)
    if not rows:
        print("outbox empty: no undelivered events")
        return 0
    print(
        _table(
            ["event_type", "pending", "retrying", "dead", "oldest_live"],
            [
                [
                    r["event_type"],
                    str(r["pending"]),
                    str(r["retrying"]),
                    str(r["dead"]),
                    "-" if r["oldest_live_s"] is None else f"{float(r['oldest_live_s']):.0f}s",
                ]
                for r in rows
            ],
        )
    )
    return 0


async def cmd_dead(conn: Any, args: argparse.Namespace) -> int:
    rows = await conn.fetch(DEAD_SQL, args.event_type, args.limit)
    if not rows:
        print("no dead-lettered events")
        return 0
    for r in rows:
        error = r["last_error"] or ""
        if not args.full:
            first = error.splitlines()[0] if error else ""
            error = first if len(first) <= 200 else first[:199] + "…"
        print(
            f"{r['id']}  {r['event_type']}  attempts={r['attempts']}  "
            f"created={r['created_at']:%Y-%m-%d %H:%M:%S}  "
            f"dead_lettered={r['dead_lettered_at']:%Y-%m-%d %H:%M:%S%z}\n    {error}"
        )
    print(f"{len(rows)} dead-lettered event(s)")
    return 0


async def cmd_requeue(conn: Any, args: argparse.Namespace) -> int:
    if args.all_dead == bool(args.ids):
        sys.exit("requeue: pass event ids or --all-dead (not both)")
    if args.all_dead:
        rows = await conn.fetch(REQUEUE_DEAD_SQL, args.event_type)
    else:
        try:
            ids = [uuid.UUID(i) for i in args.ids]
        except ValueError as err:
            sys.exit(f"requeue: invalid id: {err}")
        rows = await conn.fetch(REQUEUE_IDS_SQL, ids)
        missing = set(ids) - {r["id"] for r in rows}
        for m in sorted(missing, key=str):
            print(f"skipped {m}: not found or already delivered", file=sys.stderr)
    print(f"requeued {len(rows)} event(s)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and requeue outbox events.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="per event_type pending/retrying/dead counts")

    dead = sub.add_parser("dead", help="list dead-lettered events")
    dead.add_argument("--event-type")
    dead.add_argument("--limit", type=int, default=100)
    dead.add_argument("--full", action="store_true", help="print the full last_error")

    requeue = sub.add_parser("requeue", help="put events back in the queue")
    requeue.add_argument("ids", nargs="*", metavar="id")
    requeue.add_argument("--all-dead", action="store_true")
    requeue.add_argument("--event-type", help="with --all-dead: only this event type")
    return parser.parse_args(argv)


COMMANDS = {"stats": cmd_stats, "dead": cmd_dead, "requeue": cmd_requeue}


async def run(args: argparse.Namespace) -> int:
    try:
        import asyncpg
    except ImportError:
        sys.exit("asyncpg is required: uv run --project backend python scripts/ops/outbox.py ...")
    conn = await asyncpg.connect(database_url())
    try:
        return await COMMANDS[args.command](conn, args)
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "requeue" and args.event_type and not args.all_dead:
        sys.exit("requeue: --event-type only applies with --all-dead")
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
