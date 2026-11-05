"""Bindings come from the environment. A key never sits in source."""

from __future__ import annotations

import os
from collections.abc import Mapping

from wellbe_agent_caller.types import Binding

_OPENAI_URL = "https://api.openai.com/v1"
_OPENROUTER_URL = "https://openrouter.ai/api/v1"


def load_bindings(env: Mapping[str, str] | None = None) -> dict[str, Binding]:
    source = os.environ if env is None else env
    found: dict[str, Binding] = {}
    openai_key = source.get("OPENAI_API_KEY", "")
    if openai_key:
        found["openai"] = Binding(
            name="openai",
            base_url=source.get("WELLBE_AGENT_OPENAI_BASE_URL", _OPENAI_URL).rstrip("/"),
            api_key=openai_key,
            model=source.get("WELLBE_AGENT_OPENAI_MODEL", "gpt-4o-mini"),
            include_store_false=True,
            completion_tokens=True,
        )
    openrouter_key = source.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        headers: list[tuple[str, str]] = []
        referer = source.get("WELLBE_AGENT_OPENROUTER_REFERER", "")
        title = source.get("WELLBE_AGENT_OPENROUTER_TITLE", "")
        if referer:
            headers.append(("HTTP-Referer", referer))
        if title:
            headers.append(("X-OpenRouter-Title", title))
        found["openrouter"] = Binding(
            name="openrouter",
            base_url=source.get("WELLBE_AGENT_OPENROUTER_BASE_URL", _OPENROUTER_URL).rstrip("/"),
            api_key=openrouter_key,
            model=source.get("WELLBE_AGENT_OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            headers=tuple(headers),
            require_parameters=True,
        )
    local_url = source.get("WELLBE_AGENT_LOCAL_BASE_URL", "")
    local_model = source.get("WELLBE_AGENT_LOCAL_MODEL", "")
    if local_url and local_model:
        found["local"] = Binding(
            name="local",
            base_url=local_url.rstrip("/"),
            api_key=source.get("WELLBE_AGENT_LOCAL_API_KEY", ""),
            model=local_model,
            require_key=False,
        )
    return found


def resolve_binding(
    purpose: str,
    env: Mapping[str, str] | None = None,
    bindings: Mapping[str, Binding] | None = None,
) -> Binding | None:
    source = os.environ if env is None else env
    table = load_bindings(source) if bindings is None else bindings
    selected = source.get(f"WELLBE_AGENT_BINDING_{purpose.upper()}", "")
    if not selected:
        selected = source.get("WELLBE_AGENT_BINDING", "")
    if not selected:
        return None
    binding = table.get(selected)
    if binding is None or binding.model == "":
        return None
    if binding.require_key and binding.api_key == "":
        return None
    return binding
