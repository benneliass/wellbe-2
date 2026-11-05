"""Read one vault event.

Placement and a named content request both use this. Neither walks the
person's other records. The returned value is for the caller; it is not
written onto a context-brain node.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import httpx

from wellbe_processing_worker import ocr
from wellbe_processing_worker.ocr import DocumentText


class VaultFetchError(RuntimeError):
    """The vault could not serve an event right now; the outbox row is retried."""


class ReadKind(StrEnum):
    """What a vault read returns. Text is the default."""

    TEXT = "text"


class VaultReader:
    """One reader for a vault event. The kind selects the returned form."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def read(
        self,
        event: dict[str, Any] | str,
        *,
        kind: ReadKind | str = ReadKind.TEXT,
    ) -> DocumentText:
        """Read one event. Pass the event object or its id. No other event is read."""
        selected = kind if isinstance(kind, ReadKind) else ReadKind(kind)
        if selected is not ReadKind.TEXT:
            raise ValueError(f"unsupported vault read kind: {selected}")
        loaded = event if isinstance(event, dict) else await self._event(event)
        return await self._text(loaded)

    async def _event(self, event_id: str) -> dict[str, Any]:
        response = await self._get(f"/vault/events/{event_id}")
        event = response.json()
        if not isinstance(event, dict):
            raise VaultFetchError(f"vault event {event_id} was not an object")
        event.setdefault("id", event_id)
        return event

    async def _text(self, vault_event: dict[str, Any]) -> DocumentText:
        metadata = vault_event.get("source_metadata") or {}
        stored = metadata.get("text") or ""
        if stored:
            return DocumentText(text=str(stored))

        event_id = vault_event.get("id")
        if event_id is None:
            return DocumentText(text="")

        if vault_event.get("source_type") == "manual_text":
            response = await self._get(f"/vault/events/{event_id}/content")
            return DocumentText(text=response.content.decode("utf-8", errors="replace"))

        if _is_document(vault_event):
            response = await self._get(f"/vault/events/{event_id}/content")
            return await ocr.extract_document_text(response.content, event_id)

        return DocumentText(text="")

    async def _get(self, path: str) -> httpx.Response:
        response = await self._client.get(path)
        if response.status_code != 200:
            raise VaultFetchError(f"vault fetch {path} returned {response.status_code}")
        return response


def _is_document(vault_event: dict[str, Any]) -> bool:
    """True when the vault bytes are a PDF or a picture."""
    mime = str(vault_event.get("mime_type") or "")
    source = str(vault_event.get("source_type") or "")
    return mime == "application/pdf" or mime.startswith("image/") or source in {"pdf", "photo"}
