#!/usr/bin/env python3
"""Black-box QA journey against a deployed WellBe API.

Runs one brand-new user through the whole product with no seeding: onboarding,
every capture type, the automatic pipeline (vault -> facts -> evidence -> graph
-> genesis -> "Things noticed"), thread lifecycle, investigations/theories,
visit packets + sharing, grants/access/audit, and every read surface. Each step
asserts on *content*, not just status codes, and the run ends with a pass/fail
report (exit 1 on any failure).

    python scripts/qa/journey.py --api https://wellbe-api.tail9c487a.ts.net

On an OIDC deployment (the web app's /auth-config.js says mode "oidc") identity
headers are ignored, so the journey creates two throwaway ZITADEL users (the
patient and a second person for the grant checks), signs both in through WellBe's
login screen, and deletes them at the end. That needs the instance admin token:

    ZITADEL_PAT=... python scripts/qa/journey.py --web https://wellbe.tail9c487a.ts.net
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from oidc_identities import AuthConfig, ThrowawayUsers, fetch_auth_config, sign_in


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Journey:
    api: str
    pipeline_timeout: float
    results: list[Result] = field(default_factory=list)
    ctx: dict[str, Any] = field(default_factory=dict)

    # OIDC mode: bearer tokens of the patient and of the second person.
    token: str | None = None
    other_token: str | None = None

    def __post_init__(self) -> None:
        self.client = httpx.Client(base_url=self.api, timeout=30.0)
        self.subject = f"qa-{uuid.uuid4().hex[:10]}"

    @property
    def oidc(self) -> bool:
        return self.token is not None

    # ------------------------------------------------------------------ http
    def identity_headers(self) -> dict[str, str]:
        h = {"X-Correlation-Id": f"qa-{uuid.uuid4().hex[:12]}"}
        if self.oidc:
            h["Authorization"] = f"Bearer {self.token}"
        else:
            h.update({"X-Wellbe-Issuer": "qa-journey", "X-Wellbe-Subject": self.subject})
        return h

    def other_actor(self) -> str:
        """The second person: an onboarded OIDC user, or any unknown id in dev mode."""
        return self.ctx["other_id"] if self.oidc else str(uuid.uuid4())

    def other_controller_headers(self) -> dict[str, str]:
        """The second person acting on their own (empty) workspace."""
        if self.oidc:
            return {"Authorization": f"Bearer {self.other_token}"}
        return {"X-Wellbe-Actor-Id": self.other_actor(), "X-Wellbe-Actor-Type": "controller"}

    def headers(self, actor: str | None = None, **extra: str) -> dict[str, str]:
        pid = self.ctx["patient_id"]
        h = {
            "X-Wellbe-Actor-Id": actor or pid,
            "X-Wellbe-Patient-Id": pid,
            "X-Wellbe-Actor-Type": "controller",
            "X-Correlation-Id": f"qa-{uuid.uuid4().hex[:12]}",
        }
        h.update(extra)
        if self.oidc:
            # The token decides the actor; X-Wellbe-Actor-* are ignored by the API.
            as_other = actor is not None and actor == self.ctx.get("other_id")
            h["Authorization"] = f"Bearer {self.other_token if as_other else self.token}"
        return h

    def call(
        self, method: str, path: str, *, expect: int | tuple[int, ...] = 200, **kw: Any
    ) -> Any:
        kw.setdefault("headers", self.headers())
        resp = self.client.request(method, path, **kw)
        expected = (expect,) if isinstance(expect, int) else expect
        if resp.status_code not in expected:
            raise AssertionError(
                f"{method} {path} -> {resp.status_code} (want {expected}): {resp.text[:400]}"
            )
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.content

    # ----------------------------------------------------------------- steps
    def step(self, name: str, fn: Callable[[], str | None]) -> None:
        try:
            detail = fn() or ""
            self.results.append(Result(name, True, detail))
            print(f"  PASS  {name}  {detail}")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc) or type(exc).__name__
            self.results.append(Result(name, False, msg))
            print(f"  FAIL  {name}  {msg}")
            if not isinstance(exc, AssertionError):
                traceback.print_exc()

    def wait_for(self, what: str, fn: Callable[[], Any], timeout: float | None = None) -> Any:
        deadline = time.monotonic() + (timeout or self.pipeline_timeout)
        last: Any = None
        while time.monotonic() < deadline:
            last = fn()
            if last:
                return last
            time.sleep(2)
        raise AssertionError(f"timed out waiting for {what} (last={last!r})")


def items_of(body: Any, *keys: str) -> list[Any]:
    if isinstance(body, list):
        return body
    for k in keys + ("items",):
        if isinstance(body.get(k), list):
            return body[k]
    return []


def _pdf_with_text(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    return bytes(out)


def _image_only_pdf(text: str) -> bytes | None:
    """A 'scanned' PDF: the text exists only as pixels (no text layer), so the
    worker must OCR it. None when Pillow (>=10.1) is not installed on the runner."""
    try:
        import io

        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.load_default(size=56)
    except (ImportError, TypeError):
        return None
    img = Image.new("RGB", (120 + 34 * len(text), 200), color="white")
    ImageDraw.Draw(img).text((60, 60), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=200.0)
    return buf.getvalue()


SCANNED_LAB = "Folate: 2.1 ng/mL (ref 3-17)"

CAPTURES: list[tuple[str, dict[str, Any], str | None]] = [
    ("symptom", {"description": "Throbbing headache behind my eyes since this morning.",
                 "severity": "moderate"}, "headache"),
    ("symptom", {"description": "Headache again today, worse after screen time."}, "headache"),
    ("symptom", {"description": "Feeling very tired and low energy all week."}, "fatigue"),
    ("symptom", {"description": "Dry cough at night. No fever."}, "cough"),
    ("lab", {"test_name": "Ferritin", "value": "9", "unit": "ng/mL",
             "reference_range": "15-150"}, "ferritin"),
    ("lab", {"test_name": "Hemoglobin", "value": "11.1", "unit": "g/dL",
             "reference_range": "12.0-15.5"}, "hemoglobin"),
    ("note", {"text": "Started iron supplements. Dizziness when standing up quickly."},
     "dizziness"),
]


def run(j: Journey) -> None:
    c = j.client

    # ---------------------------------------------------------------- platform
    def health() -> str:
        body = c.get("/health").json()
        assert body.get("status") == "ok", body
        return "status=ok"

    def schema() -> str:
        body = c.get("/v2/schema").json()
        assert body, "empty schema"
        return f"{len(body)} top-level keys"

    j.step("health", health)
    j.step("v2 schema", schema)

    def unauth() -> str:
        r = c.get("/v1/threads")
        assert r.status_code == 401, r.status_code
        return "401 without identity"

    j.step("auth required", unauth)

    # -------------------------------------------------------------- onboarding
    def onboarding() -> str:
        h = j.identity_headers
        s = c.get("/v1/onboarding", headers=h()).json()
        assert s["status"] == "none", s
        assert len(s["core_consent"]) >= 1
        s = c.post("/v1/onboarding/start", json={"display_name": "QA Journey"},
                   headers=h()).json()
        assert s["status"] == "pending", s
        s = c.patch("/v1/onboarding", json={"choices": {"goal": "track"},
                                             "baseline": {"age_band": "30-39"}},
                    headers=h()).json()
        assert s["choices"].get("goal") == "track", s
        r = c.post("/v1/onboarding/finalize", json={"accept_core_consent": False},
                   headers=h())
        assert r.status_code == 422, f"finalize w/o consent -> {r.status_code}"
        s = c.post("/v1/onboarding/finalize", json={"accept_core_consent": True},
                   headers=h()).json()
        assert s["status"] == "active" and s["personal_workspace_id"], s
        again = c.post("/v1/onboarding/finalize", json={"accept_core_consent": True},
                       headers=h()).json()
        assert again["personal_workspace_id"] == s["personal_workspace_id"], "not idempotent"
        j.ctx["patient_id"] = s["controller_patient_id"]
        j.ctx["workspace_id"] = s["personal_workspace_id"]
        return f"patient={s['controller_patient_id']}"

    j.step("onboarding start/draft/finalize (+consent gate, idempotent)", onboarding)
    if "patient_id" not in j.ctx:
        return

    def workspaces() -> str:
        body = j.call("GET", "/v2/workspaces")
        items = body if isinstance(body, list) else body.get("workspaces", body.get("items", []))
        assert any(str(w.get("workspace_id", w.get("id"))) == j.ctx["workspace_id"]
                   for w in items), body
        return f"{len(items)} workspace(s)"

    j.step("workspaces lists personal workspace", workspaces)

    def empty_start() -> str:
        assert not items_of(j.call("GET", "/v1/threads"), "threads")
        assert not items_of(j.call("GET", "/v1/things-noticed"), "things_noticed")
        return "no threads, nothing noticed"

    j.step("new user starts empty (isolation from demo data)", empty_start)

    # ------------------------------------------------------------------ capture
    def capture_all() -> str:
        ids = []
        for kind, payload, _ in CAPTURES:
            key = f"qa-{uuid.uuid4()}"
            body = j.call("POST", "/v1/capture", expect=201,
                          json={"capture_type": kind, "payload": payload, "source": "qa"},
                          headers=j.headers(**{"Idempotency-Key": key}))
            assert body["status"] == "captured", body
            ids.append(body["capture_id"])
        pdf = base64.b64encode(_pdf_with_text("Vitamin B12: 180 pg/mL (ref 200-900)")).decode()
        body = j.call("POST", "/v1/capture", expect=201,
                      json={"capture_type": "document",
                            "payload": {"content_base64": pdf, "mime_type": "application/pdf",
                                        "filename": "labs.pdf"}},
                      headers=j.headers(**{"Idempotency-Key": f"qa-{uuid.uuid4()}"}))
        ids.append(body["capture_id"])
        scan_pdf = _image_only_pdf(SCANNED_LAB)
        if scan_pdf is not None:
            scan = base64.b64encode(scan_pdf).decode()
            body = j.call("POST", "/v1/capture", expect=201,
                          json={"capture_type": "document",
                                "payload": {"content_base64": scan,
                                            "mime_type": "application/pdf",
                                            "filename": "scanned-labs.pdf"}},
                          headers=j.headers(**{"Idempotency-Key": f"qa-{uuid.uuid4()}"}))
            ids.append(body["capture_id"])
            j.ctx["scanned_capture"] = body["capture_id"]
        j.ctx["capture_ids"] = ids
        return f"{len(ids)} captures (symptom/lab/note/document" + (
            "/scanned document)" if scan_pdf is not None else ")")

    j.step("capture every type", capture_all)

    def capture_idempotent() -> str:
        key = f"qa-{uuid.uuid4()}"
        req = {"capture_type": "note", "payload": {"text": "Idempotency probe."}}
        a = j.call("POST", "/v1/capture", expect=(200, 201), json=req,
                   headers=j.headers(**{"Idempotency-Key": key}))
        b = j.call("POST", "/v1/capture", expect=(200, 201), json=req,
                   headers=j.headers(**{"Idempotency-Key": key}))
        assert a["capture_id"] == b["capture_id"], (a, b)
        j.call("POST", "/v1/capture", expect=400, json=req)
        j.call("POST", "/v1/capture", expect=422,
               json={"capture_type": "symptom", "payload": {}},
               headers=j.headers(**{"Idempotency-Key": f"qa-{uuid.uuid4()}"}))
        return "replay dedupes; missing key 400; bad payload 422"

    j.step("capture idempotency + validation", capture_idempotent)

    # ------------------------------------------------ automatic pipeline/genesis
    def things_noticed() -> str:
        expected = {c[2] for c in CAPTURES if c[2]}

        def poll() -> Any:
            tn = j.call("GET", "/v1/things-noticed")
            items = items_of(tn, "things_noticed")
            text = " ".join(str(i).lower() for i in items)
            hits = {e for e in expected if e in text}
            return (items, hits) if hits >= expected else None

        try:
            items, hits = j.wait_for("genesis candidates", poll)
        except AssertionError:
            tn = j.call("GET", "/v1/things-noticed")
            items = items_of(tn, "things_noticed")
            text = " ".join(str(i).lower() for i in items)
            hits = {e for e in expected if e in text}
        j.ctx["noticed"] = items
        missing = expected - hits
        detail = f"{len(items)} candidate(s); matched {sorted(hits)}"
        assert not missing, f"{detail}; NOT surfaced: {sorted(missing)}"
        return detail

    j.step("pipeline: captures surface as Things noticed (no seeding)", things_noticed)

    def candidate_shape() -> str:
        items = j.ctx["noticed"]
        for it in items:
            assert it.get("candidate_id") or it.get("id"), it
            assert it.get("source_fact_count", 0) >= 1, f"candidate without evidence: {it}"
        return "every candidate carries evidence"

    if j.ctx.get("noticed"):
        j.step("candidates are evidence-backed", candidate_shape)

    def _cid(it: dict[str, Any]) -> str:
        return str(it.get("candidate_id") or it.get("id"))

    def _find(term: str) -> dict[str, Any] | None:
        for it in j.ctx.get("noticed", []):
            if term in str(it).lower():
                return it
        return None

    def confirm() -> str:
        confirmed = {}
        for term in ("headache", "fatigue", "ferritin"):
            it = _find(term)
            if not it:
                continue
            body = j.call("POST", f"/v1/things-noticed/{_cid(it)}/confirm", expect=(200, 201),
                          json={})
            tid = body.get("thread_id") or body.get("thread", {}).get("thread_id")
            assert tid, body
            confirmed[term] = tid
        assert confirmed, "nothing to confirm"
        j.ctx["threads"] = confirmed
        return f"confirmed {sorted(confirmed)}"

    j.step("confirm candidate -> thread", confirm)

    def dismiss() -> str:
        it = _find("cough")
        assert it, "no cough candidate"
        j.call("POST", f"/v1/things-noticed/{_cid(it)}/dismiss", expect=(200, 204), json={})
        tn = j.call("GET", "/v1/things-noticed")
        items = items_of(tn, "things_noticed")
        assert _cid(it) not in {_cid(x) for x in items}, "dismissed still listed"
        return "dismissed + hidden"

    j.step("dismiss candidate", dismiss)

    def threads() -> str:
        body = j.call("GET", "/v1/threads")
        got = {t["thread_id"] for t in items_of(body, "threads")}
        assert set(j.ctx["threads"].values()) <= got, (got, j.ctx["threads"])
        return f"{len(got)} thread(s)"

    if j.ctx.get("threads"):
        j.step("threads list shows confirmed threads", threads)

    def thread_graph() -> str:
        out = []
        for term, tid in j.ctx["threads"].items():
            g = j.call("GET", f"/v2/graph/threads/{tid}")
            n, e = len(g.get("nodes", [])), len(g.get("edges", []))
            out.append(f"{term}:{n}n/{e}e")
            assert n >= 1, f"thread graph for {term} is empty: {g}"
        return ", ".join(out)

    if j.ctx.get("threads"):
        j.step("thread graph has the evidence nodes", thread_graph)

    def thread_attach() -> str:
        tid = j.ctx["threads"].get("headache")
        assert tid, "no headache thread"
        # Same-titled memories are merged on read, so count their source links.
        def memory_count() -> int:
            memories = items_of(j.call("GET", f"/v2/threads/{tid}/memories"), "memories")
            return sum(len(m.get("source_refs") or []) for m in memories)

        before = memory_count()
        j.call("POST", "/v1/capture", expect=201,
               json={"capture_type": "symptom",
                     "payload": {"description": "Another headache this evening."}},
               headers=j.headers(**{"Idempotency-Key": f"qa-{uuid.uuid4()}"}))

        # A repeat of the same concept reuses the graph node; the attached fact
        # shows up as a new source link on the thread's memories.
        after = j.wait_for("new headache evidence attached to thread",
                           lambda: (n := memory_count()) > before and n)
        return f"follow-up capture attached to existing thread ({before} -> {after} source links)"

    if j.ctx.get("threads", {}).get("headache"):
        j.step("genesis attaches new evidence to an existing thread", thread_attach)

    def transitions() -> str:
        tid = j.ctx["threads"].get("ferritin") or next(iter(j.ctx["threads"].values()))
        t = j.call("GET", f"/v1/threads/{tid}")
        assert t["status"] == "draft", f"confirmed thread should start as draft: {t['status']}"
        for target in ("active_unresolved", "waiting_for_result"):
            t = j.call("POST", f"/v1/threads/{tid}/transition",
                       json={"target_status": target, "reason_code": "qa",
                             "expected_version": t.get("version")})
            assert t["status"] == target, t
        r = c.post(f"/v1/threads/{tid}/transition", headers=j.headers(),
                   json={"target_status": "draft", "reason_code": "qa"})
        assert r.status_code in (409, 422), f"invalid edge accepted: {r.status_code}"
        j.ctx["waiting_thread"] = tid
        r = c.post(f"/v1/threads/{tid}/transition", headers=j.headers(),
                   json={"target_status": "watchful_waiting", "reason_code": "qa",
                         "expected_version": 0})
        assert r.status_code == 409, f"stale version accepted: {r.status_code}"
        return "valid edges ok; invalid edge + stale version rejected"

    if j.ctx.get("threads"):
        j.step("thread state machine", transitions)

    def manual_thread() -> str:
        t = j.call("POST", "/v1/threads", expect=201, json={"title": "QA manual thread"})
        j.ctx["manual_thread"] = t["thread_id"]
        return t["status"]

    j.step("create thread manually", manual_thread)

    # -------------------------------------------------------- continuity/memory
    def pending() -> str:
        def poll() -> Any:
            body = j.call("GET", "/v2/pending-items")
            items = items_of(body, "pending_items")
            return items or None

        items = j.wait_for("pending items after waiting_for_result", poll, timeout=30)
        open_items = [i for i in items if i.get("status") not in ("resolved", "cancelled")]
        assert open_items, f"no open pending item: {items}"
        opened = open_items[0]
        # Time-aware: a result wait is dated by policy (transition + 7 days).
        assert opened.get("status") == "scheduled", f"not scheduled: {opened}"
        assert opened.get("due_precision") == "relative_policy", opened
        due_in = datetime.fromisoformat(opened["due_at"]) - datetime.now(UTC)
        assert timedelta(days=6, hours=23) < due_in <= timedelta(days=7, minutes=10), (
            f"due_at not ~now+7d: {opened.get('due_at')}"
        )
        j.ctx["opened_pending_item"] = opened
        return f"opened '{opened.get('title')}' scheduled, due {opened['due_at'][:10]}"

    if j.ctx.get("waiting_thread"):
        j.step("pending item opens on waiting_for_result, dated now+7d", pending)

    # Checked while the item is still open: reminders for settled items are
    # intentionally suppressed, so resolving first could race the consumer.
    def notifications() -> str:
        opened = j.ctx["opened_pending_item"]

        def poll() -> Any:
            body = j.call("GET", "/v2/notifications", params={"limit": 50})
            found = [
                n for n in items_of(body, "notifications")
                if n.get("kind") == "pending_item_created"
                and n.get("pending_item_id") == opened["pending_item_id"]
            ]
            return found or None

        found = j.wait_for("'created' notification for the waiting thread", poll, timeout=60)
        note = found[0]
        assert note.get("thread_id") == j.ctx["waiting_thread"], note
        assert note["title"] == f"New follow-up: {opened['title']}", note["title"]
        read = j.call("POST", f"/v2/notifications/{note['notification_id']}/read")
        assert read.get("read_at"), f"mark read did not set read_at: {read}"
        body = j.call("GET", "/v2/notifications", params={"limit": 50})
        again = [n for n in items_of(body, "notifications")
                 if n["notification_id"] == note["notification_id"]]
        assert again and again[0].get("read_at"), f"not read after mark: {again}"
        r = j.client.post(f"/v2/notifications/{uuid.uuid4()}/read", headers=j.headers())
        assert r.status_code == 404, f"unknown notification not 404: {r.status_code}"
        done = j.call("POST", "/v2/notifications/read-all")
        assert done.get("unread_count") == 0, done
        return f"'{note['title']}' listed; mark read + read-all ok"

    if j.ctx.get("opened_pending_item"):
        j.step("in-app notification for the opened follow-up", notifications)

    def pending_resolves() -> str:
        tid = j.ctx["waiting_thread"]
        t = j.call("GET", f"/v1/threads/{tid}")
        j.call("POST", f"/v1/threads/{tid}/transition",
               json={"target_status": "active_unresolved", "reason_code": "qa_result_in",
                     "expected_version": t.get("version")})

        def resolved() -> Any:
            body = j.call("GET", "/v2/pending-items")
            now = items_of(body, "pending_items")
            done = [i for i in now if i.get("status") == "resolved"]
            return done or None

        j.wait_for("pending item resolved after leaving waiting_for_result", resolved, timeout=30)
        return "resolved when the result came in"

    if j.ctx.get("opened_pending_item"):
        j.step("pending item resolves after leaving waiting_for_result", pending_resolves)

    def memories() -> str:
        out = []
        for term, tid in j.ctx["threads"].items():
            body = j.call("GET", f"/v2/threads/{tid}/memories")
            items = items_of(body, "memories")
            out.append(f"{term}:{len(items)}")
        assert any(not s.endswith(":0") for s in out), f"no memories: {out}"
        return ", ".join(out)

    if j.ctx.get("threads"):
        j.step("thread memories", memories)

    # ------------------------------------------------------------ read surfaces
    def patterns() -> str:
        body = j.call("GET", "/v2/patterns")
        assert body["not_diagnosis"] is True
        for p in body["patterns"]:
            assert "cause" not in p["relation_phrase"].lower()
        assert body["patterns"], "no patterns surfaced"
        return f"{len(body['patterns'])} pattern(s): " + "; ".join(
            p["relation_phrase"] for p in body["patterns"][:3])

    j.step("patterns (non-diagnostic)", patterns)

    def document_facts() -> str:
        def poll() -> Any:
            tn = j.call("GET", "/v1/things-noticed")
            return [i for i in items_of(tn, "things_noticed") if "b12" in str(i).lower()] or None

        found = j.wait_for("B12 from the PDF document", poll, timeout=30)
        return f"document lab surfaced: {found[0]['title']}"

    j.step("document (PDF) capture is extracted", document_facts)

    def scanned_document_facts() -> str:
        def poll() -> Any:
            tn = j.call("GET", "/v1/things-noticed")
            return [i for i in items_of(tn, "things_noticed")
                    if "folate" in str(i).lower()] or None

        found = j.wait_for("Folate from the scanned (image-only) PDF via local OCR", poll)
        return f"OCR'd lab surfaced: {found[0]['title']}"

    if j.ctx.get("scanned_capture"):
        j.step("scanned (image-only PDF) capture is OCR'd and extracted", scanned_document_facts)
    else:
        print("  SKIP  scanned (image-only PDF) OCR step: Pillow>=10.1 not installed "
              "(run with `uv run --with httpx --with pillow scripts/qa/journey.py ...`)")

    def delta() -> str:
        body = j.call("GET", "/v2/delta")
        items = [e for e in items_of(body, "events") if "QA manual" not in str(e)]
        assert items, f"empty delta: {str(body)[:300]}"
        return f"{len(items)} change(s)"

    j.step("delta (what changed)", delta)

    def signals() -> str:
        body = j.call("GET", "/v2/signals")
        areas = [a for a in body.get("areas", []) if a.get("status") != "no_data"]
        assert areas, f"out-of-range labs not reflected: {body.get('coverage_label')}"
        return f"{len(areas)} area(s) with data: " + ", ".join(
            f"{a['id']}={a['status']}" for a in areas)

    j.step("signals (out-of-range labs etc.)", signals)

    def ask() -> str:
        body = j.call("POST", "/v2/ask", json={"question": "What is going on with my headaches?"})
        text = str(body).lower()
        assert "headache" in text, f"answer not grounded: {str(body)[:400]}"
        assert "diagnos" not in str(body.get("answer", "")).lower()
        return str(body.get("answer", body))[:120].replace("\n", " ")

    j.step("ask grounded on threads", ask)

    def render_validate() -> str:
        j.call("POST", "/v2/render/validate", expect=428,
               json={"text": "Your ferritin causes your headaches; you have anemia."})
        return "unauthorized AI render refused (428 fail-closed)"

    j.step("render safety validator", render_validate)

    # --------------------------------------------------- investigation / theory
    def investigation() -> str:
        tids = list(j.ctx["threads"].values())[:2]
        inv = j.call("POST", "/v2/investigations", expect=201,
                     json={"primary_question": "Is low iron linked to my tiredness?",
                           "thread_ids": tids})
        iid = inv.get("investigation_id") or inv.get("id")
        j.ctx["investigation"] = iid
        got = j.call("GET", f"/v2/investigations/{iid}")
        assert set(got["health_thread_ids"]) == set(tids), got
        lst = j.call("GET", "/v2/investigations")
        assert iid in str(lst)
        inv = j.call("PATCH", f"/v2/investigations/{iid}",
                     json={"target_status": "monitoring", "reason_code": "qa"})
        assert inv["status"] == "monitoring", inv
        th = j.call("POST", f"/v2/investigations/{iid}/theories", expect=201,
                    json={"theory_text": "Low ferritin may relate to fatigue",
                          "theory_type": "symptom_cause"})
        j.ctx["theory"] = th
        ths = j.call("GET", f"/v2/investigations/{iid}/theories")
        assert "ferritin" in str(ths).lower()
        ext = j.call("GET", f"/v2/investigations/{iid}/external-context", expect=(200, 404))
        j.call("POST", f"/v2/investigations/{iid}/close", expect=409, json={"reason_code": "qa"})
        return (f"inv={iid[:8]} monitoring, theory ok, close blocked while threads unresolved, "
                f"external-context={len(ext) if isinstance(ext, list) else 'n/a'}")

    if j.ctx.get("threads"):
        j.step("investigation lifecycle + theory", investigation)

    def theory_graph() -> str:
        tid = next(iter(j.ctx["threads"].values()))
        g = j.call("GET", f"/v2/graph/threads/{tid}")
        types = {n.get("node_type", n.get("type")) for n in g.get("nodes", [])}
        assert types & {"Investigation", "investigation", "Theory", "theory"}, \
            f"investigation/theory not visible on thread graph: {types}"
        return f"node types: {sorted(map(str, types))}"

    if j.ctx.get("investigation"):
        j.step("investigation/theory linked into thread graph", theory_graph)

    def theory_evaluation() -> str:
        iid, theory = j.ctx["investigation"], j.ctx["theory"]
        theory_id = theory["theory_id"]
        inv_threads = set(j.call("GET", f"/v2/investigations/{iid}")["health_thread_ids"])
        tid = j.ctx["threads"].get("headache")
        assert tid in inv_threads, f"headache thread not in investigation: {inv_threads}"

        memories = items_of(j.call("GET", f"/v2/threads/{tid}/memories"), "memories")
        facts = [
            ref["source_ref_id"]
            for m in memories if "headache" in str(m.get("title", "")).lower()
            for ref in m.get("source_refs", [])
            if ref.get("source_ref_type") == "c4_extracted_fact"
        ]
        assert facts, f"no headache fact to cite on thread memories: {memories}"
        evidence = [{"kind": "fact", "id": facts[0]}]
        version = theory.get("version", 1)
        path = f"/v2/theories/{theory_id}/evaluate"
        rationale = "Headaches continued on days my iron was fine."

        no_ev = j.call("POST", path, expect=422, json={
            "to_status": "weakened", "rationale": rationale, "evidence_refs": [],
            "expected_version": version})
        assert no_ev["code"] == "theory_evidence_required", no_ev
        stale = j.call("POST", path, expect=409, json={
            "to_status": "weakened", "rationale": rationale, "evidence_refs": evidence,
            "expected_version": version + 5})
        assert stale["code"] == "version_conflict", stale

        out = j.call("POST", path, json={
            "to_status": "weakened", "rationale": rationale, "evidence_refs": evidence,
            "expected_version": version})
        updated, ev = out["theory"], out["evaluation"]
        assert updated["status"] == "not_supported_by_current_data", updated
        assert updated["version"] == version + 1, updated
        assert updated["assessment_label"] == "You marked this theory as weakened", updated
        assert updated["not_diagnosis"] is True
        assert ev["evidence_refs"] == evidence, ev

        history = j.call("GET", f"/v2/theories/{theory_id}/evaluations")
        assert history and history[0]["evaluation_id"] == ev["evaluation_id"], history
        listed = j.call("GET", f"/v2/investigations/{iid}/theories")
        mine = next(t for t in listed if t["theory_id"] == theory_id)
        assert mine["latest_evaluation"]["assessment"] == "weakened", mine

        g = j.call("GET", f"/v2/graph/threads/{tid}")
        theory_nodes = {n["id"] for n in g.get("nodes", []) if n.get("type") == "Theory"}
        against = [e for e in g.get("edges", [])
                   if e.get("relation") == "evidence_against" and e.get("target") in theory_nodes]
        assert against, (
            f"no evidence_against edge to the theory on thread graph: "
            f"theory_nodes={theory_nodes} edges={[e.get('relation') for e in g.get('edges', [])]}"
        )
        return (f"marked weakened citing fact {facts[0][:8]}; 422 without evidence, 409 on "
                f"stale version; {len(against)} evidence_against edge(s) on thread graph")

    if j.ctx.get("theory") and j.ctx.get("threads", {}).get("headache"):
        j.step("user evaluates theory (weakened) with cited evidence", theory_evaluation)

    # ------------------------------------------------------------ visit packets
    def visit_packet() -> str:
        tids = list(j.ctx["threads"].values())
        pk = j.call("POST", "/v2/visit-packets", expect=201,
                    json={"title": "QA visit", "thread_ids": tids,
                          "prep": {"questions": ["Should I recheck iron?"]}})
        pid = pk["packet_id"]
        pk = j.call("GET", f"/v2/visit-packets/{pid}")
        stmts = pk.get("statements", [])
        assert stmts, f"packet has no statements: {str(pk)[:300]}"
        first = stmts[0].get("statement_id")
        if first:
            j.call("PATCH", f"/v2/visit-packets/{pid}",
                   json={"inclusions": [{"statement_id": first, "included": False}]})
        share = j.call("POST", f"/v2/visit-packets/{pid}/share", expect=(200, 201),
                       json={"recipient_name": "Dr QA", "expires_in_hours": 1})
        token = share.get("token") or share.get("share_token")
        assert token, share
        shared = c.get(f"/v2/share/{token}")
        assert shared.status_code == 200, f"shared read {shared.status_code}: {shared.text[:200]}"
        exp = c.post(f"/v2/visit-packets/{pid}/export", headers=j.headers(), json={})
        assert exp.status_code in (200, 201) and exp.content, f"export {exp.status_code}"
        link_id = share.get("share_link_id")
        assert link_id, f"share response has no link id: {share}"
        j.call("POST", f"/v2/visit-packets/{pid}/share/{link_id}/revoke", expect=(200, 204),
               json={})
        after = c.get(f"/v2/share/{token}")
        assert after.status_code in (403, 404, 410), (
            f"revoked share still readable {after.status_code}"
        )
        ctype = exp.headers.get("content-type")
        return f"{len(stmts)} statement(s); share/read/export/revoke ok ({ctype})"

    if j.ctx.get("threads"):
        j.step("visit packet compose/edit/share/export/revoke", visit_packet)

    # ------------------------------------------------------ access / grants / audit
    def grants() -> str:
        other = j.other_actor()
        tid = next(iter(j.ctx["threads"].values()))
        r = c.get(f"/v1/threads/{tid}", headers=j.headers(actor=other, **{
            "X-Wellbe-Actor-Type": "caregiver"}))
        assert r.status_code in (403, 404), f"stranger read thread: {r.status_code}"
        ev = j.call("POST", "/v2/access/evaluate",
                    json={"resource_type": "health_thread", "action": "read"})
        g = j.call("POST", "/v2/grants", expect=(200, 201),
                   json={"grantee_type": "user", "grantee_user_id": other,
                         "actions": ["read"], "data_categories": ["health_thread"],
                         "thread_ids": [tid], "purpose": "care_coordination"})
        gid = g.get("grant_id") or g.get("id")
        r = c.get(f"/v1/threads/{tid}", headers=j.headers(actor=other, **{
            "X-Wellbe-Actor-Type": "caregiver"}))
        assert r.status_code in (403, 404), f"pending grant already reads: {r.status_code}"
        j.call("POST", f"/v2/grants/{gid}/accept", json={},
               headers=j.headers(actor=other, **{"X-Wellbe-Actor-Type": "caregiver"}))
        r = c.get(f"/v1/threads/{tid}", headers=j.headers(actor=other, **{
            "X-Wellbe-Actor-Type": "caregiver"}))
        granted = r.status_code
        others = [t for t in j.ctx["threads"].values() if t != tid]
        if others:
            r2 = c.get(f"/v1/threads/{others[0]}", headers=j.headers(actor=other, **{
                "X-Wellbe-Actor-Type": "caregiver"}))
            assert r2.status_code in (403, 404), f"grant leaked unshared thread: {r2.status_code}"
        lst = j.call("GET", "/v2/grants")
        assert gid in str(lst)
        j.call("POST", f"/v2/grants/{gid}/revoke", expect=(200, 204), json={"reason": "qa"})
        r = c.get(f"/v1/threads/{tid}", headers=j.headers(actor=other, **{
            "X-Wellbe-Actor-Type": "caregiver"}))
        assert r.status_code in (403, 404), f"revoked grant still reads: {r.status_code}"
        assert granted == 200, f"granted caregiver could not read thread ({granted})"
        return (f"evaluate={ev.get('decision')}; pending denied, accepted 200, unshared thread "
                f"denied, revoked {r.status_code}")

    if j.ctx.get("threads"):
        j.step("grants: deny, grant, read, revoke", grants)

    def audit() -> str:
        body = j.call("GET", "/v2/audit/my-events")
        items = items_of(body, "events")
        assert items, "no audit events"
        return f"{len(items)} audit event(s)"

    j.step("audit trail", audit)

    def corrections() -> str:
        tid = next(iter(j.ctx["threads"].values()))
        body = j.call("POST", "/v2/corrections", expect=(200, 201, 202),
                      json={"correction_type": "relabel_thread",
                            "target": {"target_kind": "c7_thread_label", "target_id": tid},
                            "raw_correction_event_id": str(uuid.uuid4()),
                            "proposed_payload": {"title": "Headaches (screen related?)"},
                            "rationale": "qa"})
        listed = j.call("GET", "/v2/corrections")
        assert any(tid in str(x) for x in items_of(listed, "corrections")), "correction not listed"
        return f"status={body.get('status')}"

    if j.ctx.get("threads"):
        j.step("corrections", corrections)

    def isolation() -> str:
        h = j.other_controller_headers()
        th = c.get("/v1/threads", headers=h).json()
        assert not items_of(th, "threads"), f"leak: {th}"
        pt = c.get("/v2/patterns", headers=h).json()
        assert not pt.get("patterns"), "pattern leak"
        return "another controller sees nothing"

    j.step("patient isolation", isolation)


def onboard_other(j: Journey) -> None:
    """Make the second OIDC person an active account, so grants can name them."""
    h = {"Authorization": f"Bearer {j.other_token}"}
    c = j.client
    c.post("/v1/onboarding/start", json={"display_name": "QA Other"}, headers=h)
    s = c.post("/v1/onboarding/finalize", json={"accept_core_consent": True}, headers=h).json()
    assert s.get("status") == "active", f"second person onboarding: {s}"
    j.ctx["other_id"] = s["controller_patient_id"]


def start_oidc(j: Journey, web: str, config: AuthConfig, users: ThrowawayUsers) -> None:
    main_name, other_name = f"{j.subject}", f"{j.subject}-other"
    main_pw = users.create(main_name, "QA Journey")
    other_pw = users.create(other_name, "QA Other")
    j.token = sign_in(web, config, main_name, main_pw)
    j.other_token = sign_in(web, config, other_name, other_pw)
    onboard_other(j)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://wellbe-api.tail9c487a.ts.net")
    ap.add_argument(
        "--web",
        default="https://wellbe.tail9c487a.ts.net",
        help="web origin; its /auth-config.js decides dev-headers vs OIDC identities",
    )
    ap.add_argument("--pipeline-timeout", type=float, default=90)
    args = ap.parse_args()
    j = Journey(api=args.api, pipeline_timeout=args.pipeline_timeout)
    web = args.web.rstrip("/")
    config = fetch_auth_config(web)
    users: ThrowawayUsers | None = None
    if config.mode == "oidc":
        admin = os.environ.get("ZITADEL_PAT", "").strip()
        if not admin:
            sys.exit("OIDC deployment: set ZITADEL_PAT (instance admin token) to create QA users")
        users = ThrowawayUsers(config.issuer, admin)
    try:
        if users:
            start_oidc(j, web, config, users)
            print(f"QA journey against {args.api} as OIDC users {j.subject}(+-other), "
                  f"signed in via {web}/login")
        else:
            print(f"QA journey against {args.api} as subject {j.subject}")
        run(j)
    finally:
        if users:
            users.cleanup()
    failed = [r for r in j.results if not r.ok]
    print(f"\n{len(j.results) - len(failed)}/{len(j.results)} passed")
    for r in failed:
        print(f"  - {r.name}: {r.detail}")
    print(f"patient_id={j.ctx.get('patient_id')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
