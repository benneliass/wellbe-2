"""The three purposes that share this caller. Later purposes register beside them."""

from __future__ import annotations

from wellbe_agent_caller.types import Purpose

KEYWORD_PASS = "keyword_pass"
LINK_JUDGMENT = "link_judgment"
VISION_READ = "vision_read"

_IMAGE_TYPES = ("image/png", "image/jpeg")

_KEYWORD_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["keywords"],
    "properties": {
        "keywords": {
            "type": "array",
            "minItems": 5,
            "maxItems": 10,
            "items": {"type": "string"},
        }
    },
}

_LINK_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "reason", "handle"],
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["link", "no_link", "uncertain", "open_content", "walk", "standalone"],
        },
        "reason": {"type": "string"},
        "handle": {"type": ["string", "null"]},
    },
}


def builtin_purposes() -> dict[str, Purpose]:
    return {
        KEYWORD_PASS: Purpose(
            name=KEYWORD_PASS,
            kind="schema",
            deadline_ms=15_000,
            max_tokens=200,
            send_fields=("text",),
            schema=_KEYWORD_SCHEMA,
            checks=("keywords_in_text",),
            instruction=(
                "Return JSON with one field, keywords: five to ten short strings that appear "
                "in the note. Use the note's own words."
            ),
        ),
        LINK_JUDGMENT: Purpose(
            name=LINK_JUDGMENT,
            kind="schema",
            deadline_ms=20_000,
            max_tokens=300,
            send_fields=("instruction", "content"),
            check_fields=("issued_handles",),
            schema=_LINK_SCHEMA,
            checks=("issued_handle",),
        ),
        VISION_READ: Purpose(
            name=VISION_READ,
            kind="text",
            deadline_ms=60_000,
            max_tokens=4_000,
            image_field="page",
            media_type_field="media_type",
            instruction="Transcribe this page. Return only the words you can read.",
        ),
    }


def allowed_media_types() -> tuple[str, ...]:
    return _IMAGE_TYPES
