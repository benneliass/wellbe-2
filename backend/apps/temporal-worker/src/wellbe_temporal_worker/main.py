"""Temporal Worker: registers and runs all durable workflow activities."""

from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from wellbe_temporal_worker.workflows.document_ocr import (
    DocumentOCRWorkflow,
    ocr_with_paddleocr,
    ocr_with_tesseract,
    ocr_with_vision_llm,
    store_ocr_results,
)


async def main() -> None:
    temporal_host = os.environ.get("WELLBE_TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(temporal_host)

    worker = Worker(
        client,
        task_queue="wellbe-ocr",
        workflows=[DocumentOCRWorkflow],
        activities=[
            ocr_with_paddleocr,
            ocr_with_tesseract,
            ocr_with_vision_llm,
            store_ocr_results,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
