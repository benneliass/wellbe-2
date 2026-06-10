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
