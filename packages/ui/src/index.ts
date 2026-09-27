// Foundation
export { Icon } from "./Icon";
export type { IconName, IconProps } from "./Icon";

// Primitives (ported from the WellBe design system prototype)
export { Chip } from "./primitives/Chip";
export type { ChipProps, Tone } from "./primitives/Chip";
export { ConfidenceDots } from "./primitives/ConfidenceDots";
export type { ConfidenceDotsProps } from "./primitives/ConfidenceDots";
export { Button } from "./primitives/Button";
export type { ButtonProps, ButtonVariant } from "./primitives/Button";
export { SourceChip, SOURCE_META } from "./primitives/SourceChip";
export type { SourceChipProps, SourceType } from "./primitives/SourceChip";
export { Modal } from "./primitives/Modal";
export type { ModalProps } from "./primitives/Modal";

// On-demand building blocks (design-system elements available for adoption)
export { Card } from "./primitives/Card";
export type { CardProps, CardVariant } from "./primitives/Card";
export { StatefulCard } from "./primitives/StatefulCard";
export type { StatefulCardProps, CardState } from "./primitives/StatefulCard";
export { MetricCard } from "./primitives/MetricCard";
export type { MetricCardProps, MetricDelta } from "./primitives/MetricCard";
export { Tabs } from "./primitives/Tabs";
export type { TabsProps, TabItem } from "./primitives/Tabs";
export { Pagination } from "./primitives/Pagination";
export type { PaginationProps } from "./primitives/Pagination";
export { SearchInput } from "./primitives/SearchInput";
export type { SearchInputProps } from "./primitives/SearchInput";
export { VerificationBadge } from "./primitives/VerificationBadge";
export type { VerificationBadgeProps, VerificationKind } from "./primitives/VerificationBadge";
export { Wordmark } from "./primitives/Wordmark";
export type { WordmarkProps } from "./primitives/Wordmark";

// Safety / semantic layer (existing — calm state tokens + evidence markers)
export { STATE_TOKENS, STATE_MARK_VARS, FONT_VARS, TYPE_SCALE_VARS, MOTION_VARS } from "./tokens";
export type { StateToken, StateTokenMeta, DisclosureLevel } from "./tokens";
export { StatePill } from "./components/StatePill";
export type { StatePillProps } from "./components/StatePill";
export { DisclosureRegion } from "./components/DisclosureRegion";
export type { DisclosureRegionProps } from "./components/DisclosureRegion";

// Evidence primitives (WEL-144), Journey Rail (WEL-139), Story lanes (WEL-146)
export { EVIDENCE_TOKENS } from "./tokens";
export type { EvidenceToken, EvidenceTokenMeta } from "./tokens";
export type {
  SourceComponent,
  SourceKind,
  ReviewMarkerValue,
  ConfidenceLevel,
  CorrectionState,
  CorrectionInfo,
  EvidenceSource,
} from "./evidence/types";
export {
  looksLikeRawId,
  resolveDisplayLabel,
  containsBannedPhrasing,
  BANNED_CANDIDATE_PHRASES,
  SOURCE_COMPONENT_LABEL,
} from "./evidence/format";
export { SourceMarker } from "./evidence/SourceMarker";
export type { SourceMarkerProps } from "./evidence/SourceMarker";
export { ConfidenceMeter, bucketConfidence, CONFIDENCE_COPY } from "./evidence/ConfidenceMeter";
export type { ConfidenceMeterProps } from "./evidence/ConfidenceMeter";
export { ReviewMarker, ReviewMarkerList, REVIEW_MARKER_LABELS } from "./evidence/ReviewMarker";
export type { ReviewMarkerProps, ReviewMarkerListProps } from "./evidence/ReviewMarker";
export { CorrectionMarker } from "./evidence/CorrectionMarker";
export type { CorrectionMarkerProps } from "./evidence/CorrectionMarker";
export { EvidenceDrawer } from "./evidence/EvidenceDrawer";
export type { EvidenceDrawerProps } from "./evidence/EvidenceDrawer";
export {
  JourneyRail,
  mapThreadStatusToStage,
  stageTone,
  traveledStages,
  JOURNEY_STAGE_LABELS,
  THREAD_STATUS_LABELS,
} from "./evidence/JourneyRail";
export type { JourneyRailProps, JourneyStage, HealthThreadStatus } from "./evidence/JourneyRail";
export { StoryLanes, laneForAuthorship, STORY_LANE_COPY, LIFECYCLE_LABELS } from "./evidence/StoryLanes";
export type {
  StoryLanesProps,
  StoryEntry,
  StoryLane,
  AuthorshipMode,
  MemoryLifecycleState,
} from "./evidence/StoryLanes";
export { RelevanceCandidateCard, CANDIDATE_COPY } from "./evidence/RelevanceCandidateCard";
export type { RelevanceCandidateCardProps } from "./evidence/RelevanceCandidateCard";
