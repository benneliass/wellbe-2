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
export { STATE_TOKENS } from "./tokens";
export type { StateToken, StateTokenMeta, DisclosureLevel } from "./tokens";
export { StatePill } from "./components/StatePill";
export type { StatePillProps } from "./components/StatePill";
export { DisclosureRegion } from "./components/DisclosureRegion";
export type { DisclosureRegionProps } from "./components/DisclosureRegion";
export {
  SourceMarker,
  ReviewMarker,
  ConfidenceMeter,
  CorrectionMarker,
  bucketConfidence,
} from "./components/markers";
export type { ReviewMarkerValue, ConfidenceLevel } from "./components/markers";
