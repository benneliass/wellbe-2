#!/usr/bin/env python3
"""Record user-provided research verbatim into a decision record.

Two modes:
  open   — splice research under "## Research provided" (bounded by
           "## Approaches considered") for an OPEN decision record.
  append — add a clearly-marked re-run addendum before the append-only
           footer of an already-APPROVED decision record (decision unchanged).

Per .cursor/rules/research-protocol.mdc Section D, the agent records research
faithfully and never edits an approved decision in place.
"""
import argparse
import os


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--mode", choices=["open", "append"], required=True)
    ap.add_argument("--date", default="2026-06-18")
    args = ap.parse_args()

    research = open(args.research, encoding="utf-8").read().strip()
    record = open(args.record, encoding="utf-8").read()
    src = os.path.basename(args.research)

    if args.mode == "open":
        start = record.index("## Research provided")
        end = record.index("## Approaches considered")
        note = (
            f"> User-provided research, recorded verbatim per research-protocol.mdc "
            f"Section D (received {args.date}). Source file: `{src}`. "
            f"Not synthesised by the agent.\n\n"
        )
        block = "## Research provided\n\n" + note + research + "\n\n"
        new = record[:start] + block + record[end:]
    else:  # append
        footer = "\n---\n\n_This record is append-only"
        idx = record.index(footer)
        addendum = (
            f"## Re-run research (user-provided, {args.date})\n\n"
            f"> Recorded per research-protocol.mdc Section D. The approved decision above "
            f"is unchanged. This independent re-run research was reviewed and is consistent "
            f"with the approved decision; no supersede. Source file: `{src}`.\n\n"
            + research
        )
        new = record[:idx] + "\n\n" + addendum.rstrip() + "\n" + record[idx:]

    open(args.record, "w", encoding="utf-8").write(new)
    print(f"Wrote {args.record} (mode={args.mode}, research={src})")


if __name__ == "__main__":
    main()
