from wellbe_c4_processing.dispatcher import DispatchDecision, DispatchRoute, decide_route
from wellbe_c4_processing.extractor import (
    PIPELINE_VERSION,
    STRUCTURED_CONTRACT_VERSION,
    ExtractionResult,
    FactExtractor,
    StructuredObservationExtractor,
    TextFactExtractor,
    compute_quality_flag,
)
from wellbe_c4_processing.investigation_extractor import (
    ExternalClaimExtractor,
    ExternalClaimResult,
    TheoryClaimExtractor,
    TheoryClaimResult,
)
from wellbe_c4_processing.models import ExtractedFactRow, HealthSignalRow
from wellbe_c4_processing.repository import ProcessingRepository
from wellbe_c4_processing.vital_registry import (
    VITAL_REGISTRY_VERSION,
    VitalConcept,
    classify_vital,
)

__all__ = [
    "DispatchDecision",
    "DispatchRoute",
    "ExternalClaimExtractor",
    "ExternalClaimResult",
    "ExtractionResult",
    "ExtractedFactRow",
    "FactExtractor",
    "HealthSignalRow",
    "PIPELINE_VERSION",
    "STRUCTURED_CONTRACT_VERSION",
    "ProcessingRepository",
    "StructuredObservationExtractor",
    "TextFactExtractor",
    "TheoryClaimExtractor",
    "TheoryClaimResult",
    "VITAL_REGISTRY_VERSION",
    "VitalConcept",
    "classify_vital",
    "compute_quality_flag",
    "decide_route",
]
