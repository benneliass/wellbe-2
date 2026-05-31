from __future__ import annotations

import uuid

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


def configure_tracing(service_name: str) -> None:
    """Initialise a no-op TracerProvider for local dev.

    In deployed environments, an OTEL collector sidecar injects the real
    exporter via OTEL_TRACES_EXPORTER / OTEL_EXPORTER_OTLP_ENDPOINT env vars,
    so this function is intentionally minimal.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)


def get_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id != 0:
        return format(ctx.trace_id, "032x")
    return uuid.uuid4().hex
