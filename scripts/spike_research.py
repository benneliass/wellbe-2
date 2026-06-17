#!/usr/bin/env python3
"""Agent-run spike research runner (research-protocol.mdc Section I).

Takes a Research Context Packet (the prompt) and runs it against the configured
LLM, then records the raw model output verbatim into a Decision Record under the
"Research provided" section, attributed as required by Section I.

Design constraints (do not relax without updating Section I):
  * The API key is read ONLY from the WELLBE_RESEARCH_API_KEY environment
    variable. It is never logged, printed, or written to any file.
  * stdlib-only (urllib) so this script needs no extra dependencies and is kept
    out of shipped images.
  * Uses the OpenAI Responses API (/v1/responses) with web_search enabled, in
    background mode with polling, since these runs take minutes.
  * Records output verbatim. It does NOT synthesise, paraphrase, or decide. The
    agent writes "Approaches considered" + a proposed "Decision" separately, and
    the user still approves before the Spike closes.

Usage:
    export WELLBE_RESEARCH_API_KEY=sk-...        # never committed
    python scripts/spike_research.py \
        --packet docs/decisions/<slug>.research-packet.md \
        --decision-record docs/decisions/<slug>.md

Optional env (with defaults):
    WELLBE_RESEARCH_MODEL      default: gpt-5.5-pro
    WELLBE_RESEARCH_BASE_URL   default: https://api.openai.com/v1
    WELLBE_RESEARCH_WEB_SEARCH default: "1" (set "0" to disable the web_search tool)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("WELLBE_RESEARCH_MODEL", "gpt-5.5-pro")
DEFAULT_BASE_URL = os.environ.get("WELLBE_RESEARCH_BASE_URL", "https://api.openai.com/v1").rstrip("/")
WEB_SEARCH_ENABLED = os.environ.get("WELLBE_RESEARCH_WEB_SEARCH", "1") not in ("0", "false", "False", "")
KEY_ENV = "WELLBE_RESEARCH_API_KEY"

# Poll up to ~20 minutes; these deep web-search runs can be slow.
POLL_INTERVAL_SECONDS = 10
POLL_MAX_ATTEMPTS = 120
RESEARCH_MARKER = "## Research provided"


class ResearchError(RuntimeError):
    pass


def _require_key() -> str:
    key = os.environ.get(KEY_ENV)
    if not key:
        raise ResearchError(
            f"{KEY_ENV} is not set. Export your rotated research key first:\n"
            f"  export {KEY_ENV}=sk-...\n"
            "The key is read from the environment only and is never written to disk."
        )
    return key


def _request(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # surface body without leaking the key
        body = exc.read().decode("utf-8", errors="replace")
        raise ResearchError(f"HTTP {exc.code} from {method} {url}: {body}") from None
    except urllib.error.URLError as exc:
        raise ResearchError(f"Network error calling {method} {url}: {exc.reason}") from None


def start_run(prompt: str, key: str) -> str:
    payload: dict = {
        "model": DEFAULT_MODEL,
        "input": prompt,
        "background": True,
    }
    if WEB_SEARCH_ENABLED:
        payload["tools"] = [{"type": "web_search"}]
    result = _request("POST", f"{DEFAULT_BASE_URL}/responses", key, payload)
    run_id = result.get("id")
    if not run_id:
        raise ResearchError(f"No response id returned: {json.dumps(result)[:500]}")
    return run_id


def poll_run(run_id: str, key: str) -> dict:
    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        result = _request("GET", f"{DEFAULT_BASE_URL}/responses/{run_id}", key)
        status = result.get("status")
        if status in ("completed", "failed", "cancelled", "incomplete"):
            if status != "completed":
                raise ResearchError(f"Run {run_id} ended with status={status}: {json.dumps(result)[:800]}")
            return result
        print(f"  [{attempt}/{POLL_MAX_ATTEMPTS}] status={status}; waiting {POLL_INTERVAL_SECONDS}s...", flush=True)
        time.sleep(POLL_INTERVAL_SECONDS)
    raise ResearchError(f"Run {run_id} did not complete within the polling window.")


def extract_text(result: dict) -> str:
    """Pull the model's text output out of a Responses API result."""
    text = result.get("output_text")
    if isinstance(text, str) and text.strip():
        return text
    chunks: list[str] = []
    for item in result.get("output", []) or []:
        for part in item.get("content", []) or []:
            if part.get("type") in ("output_text", "text") and part.get("text"):
                chunks.append(part["text"])
    if not chunks:
        raise ResearchError(f"Could not find text output in result: {json.dumps(result)[:800]}")
    return "\n\n".join(chunks)


def record_into_decision_record(record_path: str, model: str, run_id: str, raw_output: str) -> None:
    today = _dt.date.today().isoformat()
    block = (
        f"{RESEARCH_MARKER}\n\n"
        f"> Agent-run LLM research (model: {model}, date: {today}, run id: {run_id}, "
        f"web_search: {'on' if WEB_SEARCH_ENABLED else 'off'}). "
        f"Recorded verbatim per research-protocol.mdc Section I. Not synthesised by the agent.\n\n"
        f"{raw_output.strip()}\n"
    )
    if not os.path.exists(record_path):
        raise ResearchError(f"Decision Record not found: {record_path} (create the stub first).")
    with open(record_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    if RESEARCH_MARKER in content:
        head, _, tail = content.partition(RESEARCH_MARKER)
        # Replace from the marker to the next top-level heading (## ) or EOF.
        rest = tail
        next_idx = rest.find("\n## ")
        remainder = rest[next_idx:] if next_idx != -1 else ""
        content = head + block + ("\n" + remainder.lstrip("\n") if remainder else "")
    else:
        content = content.rstrip() + "\n\n" + block
    with open(record_path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run agent spike research (Section I).")
    parser.add_argument("--packet", required=True, help="Path to the Research Context Packet (the prompt).")
    parser.add_argument("--decision-record", required=True, help="Path to the Decision Record to record into.")
    parser.add_argument("--print-only", action="store_true", help="Print output instead of writing to the record.")
    args = parser.parse_args(argv)

    try:
        key = _require_key()
        with open(args.packet, "r", encoding="utf-8") as fh:
            prompt = fh.read()
        if not prompt.strip():
            raise ResearchError(f"Packet is empty: {args.packet}")

        print(f"Starting research run (model={DEFAULT_MODEL}, web_search={'on' if WEB_SEARCH_ENABLED else 'off'})...", flush=True)
        run_id = start_run(prompt, key)
        print(f"Run started: {run_id}. Polling for completion...", flush=True)
        result = poll_run(run_id, key)
        output = extract_text(result)

        if args.print_only:
            print("\n----- RAW MODEL OUTPUT -----\n")
            print(output)
        else:
            record_into_decision_record(args.decision_record, DEFAULT_MODEL, run_id, output)
            print(f"Recorded verbatim into {args.decision_record} under '{RESEARCH_MARKER}'.", flush=True)
        return 0
    except ResearchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
