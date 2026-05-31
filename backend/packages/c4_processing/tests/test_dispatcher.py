from __future__ import annotations

import pytest

from wellbe_c4_processing.dispatcher import (
    DispatchRoute,
    decide_route,
)


class TestDecideRoute:
    def test_manual_text_routes_to_dramatiq(self):
        decision = decide_route("manual_text", "text/plain")
        assert decision.route == DispatchRoute.DRAMATIQ_TEXT
        assert decision.source_type == "manual_text"

    def test_sms_routes_to_dramatiq(self):
        decision = decide_route("sms", "text/plain")
        assert decision.route == DispatchRoute.DRAMATIQ_TEXT

    def test_device_routes_to_dramatiq(self):
        decision = decide_route("device", "application/json")
        assert decision.route == DispatchRoute.DRAMATIQ_TEXT

    def test_image_jpeg_routes_to_temporal_ocr(self):
        decision = decide_route("photo", "image/jpeg")
        assert decision.route == DispatchRoute.TEMPORAL_OCR

    def test_image_png_routes_to_temporal_ocr(self):
        decision = decide_route("photo", "image/png")
        assert decision.route == DispatchRoute.TEMPORAL_OCR

    def test_pdf_routes_to_temporal_ocr(self):
        decision = decide_route("pdf", "application/pdf")
        assert decision.route == DispatchRoute.TEMPORAL_OCR

    def test_fhir_routes_to_temporal_fhir(self):
        decision = decide_route("fhir", "application/fhir+json")
        assert decision.route == DispatchRoute.TEMPORAL_FHIR

    def test_unknown_source_routes_to_temporal_document(self):
        decision = decide_route("unknown", "text/html")
        assert decision.route == DispatchRoute.TEMPORAL_DOCUMENT

    def test_fhir_takes_priority_over_mime(self):
        decision = decide_route("fhir", "image/jpeg")
        assert decision.route == DispatchRoute.TEMPORAL_FHIR
